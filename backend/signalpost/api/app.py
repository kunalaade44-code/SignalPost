import asyncio
import json
import logging
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from signalpost.agent.graph import SignalpostAgent
from signalpost.config import settings
from signalpost.connectors.brreg_enheter import BrregEnheterConnector
from signalpost.core.checksum import validate_org_number
from signalpost.schemas.profile import CompanyProfile
from signalpost.storage.database import (
    engine,
    get_profile_by_orgnr,
    get_profile_history,
    init_db,
    is_profile_fresh,
    save_or_update_profile,
)
from signalpost.storage.models import CompanyHistoryModel, CompanyProfileModel, FactModel
from signalpost.storage.supabase_sync import supabase_sync
from sqlmodel import Session, func, select

logger = logging.getLogger(__name__)

# Active background runs state tracking
ACTIVE_RUNS: dict[str, dict[str, Any]] = {}

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Signalpost API",
    description="REST API for autonomous Norwegian company profiling, verification, and audit tracking.",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api")
def api_index():
    """API overview and discovery index."""
    return {
        "app": settings.app_name,
        "version": "0.1.0",
        "status": "online",
        "docs_url": "/api/docs",
        "health_url": "/api/health",
        "stats_url": "/api/stats",
    }


class BatchRunRequest(BaseModel):
    org_numbers: list[str] = Field(..., description="List of 9-digit Norwegian organization numbers")
    concurrency: int = Field(default=6, ge=1, le=16)
    force_refresh: bool = Field(default=False)


class AddCompanyRequest(BaseModel):
    org_number: str = Field(..., description="9-digit Norwegian organization number")
    force_refresh: bool = Field(default=False)
    track: bool = Field(default=True)


class BulkAddCompaniesRequest(BaseModel):
    org_numbers: list[str] = Field(..., description="List of Norwegian organization numbers")
    track: bool = Field(default=True)
    concurrency: int = Field(default=6, ge=1, le=16)
    force_refresh: bool = Field(default=False)


@app.get("/api/health")
def health_check():
    """Health check endpoint confirming API status and database connectivity."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "environment": settings.app_env,
        "llm_provider": settings.llm_provider,
        "supabase_configured": supabase_sync.is_configured,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/api/stats")
def get_system_stats():
    """Returns database summary statistics and budget limits snapshot."""
    with Session(engine) as session:
        total_profiles = session.exec(select(func.count(CompanyProfileModel.org_number))).one()
        active_count = session.exec(
            select(func.count(CompanyProfileModel.org_number)).where(CompanyProfileModel.status == "ACTIVE")
        ).one()
        bankrupt_count = session.exec(
            select(func.count(CompanyProfileModel.org_number)).where(CompanyProfileModel.status == "BANKRUPT")
        ).one()
        total_facts = session.exec(select(func.count(FactModel.id))).one()
        total_history = session.exec(select(func.count(CompanyHistoryModel.id))).one()

        # Latest profiles
        latest_profiles_stmt = (
            select(CompanyProfileModel)
            .order_by(CompanyProfileModel.last_checked_at.desc())
            .limit(10)
        )
        latest_profiles = [
            {
                "org_number": p.org_number,
                "legal_name": p.legal_name,
                "status": p.status,
                "org_form": p.org_form,
                "employees": p.employees,
                "facts_count": p.facts_count,
                "last_checked_at": p.last_checked_at,
            }
            for p in session.exec(latest_profiles_stmt).all()
        ]

    return {
        "database": {
            "total_profiles": total_profiles,
            "active_profiles": active_count,
            "bankrupt_profiles": bankrupt_count,
            "total_verified_facts": total_facts,
            "total_audit_events": total_history,
        },
        "limits": {
            "max_requests": settings.max_requests_total,
            "max_cost_usd": settings.max_cost_usd,
            "max_run_time_seconds": settings.max_run_time_seconds,
        },
        "recent_profiles": latest_profiles,
    }


@app.get("/api/company/{orgnr}", response_model=CompanyProfile)
async def get_company_profile(
    orgnr: str,
    force: bool = Query(default=False, description="Force live re-crawl bypassing cache"),
):
    """
    Retrieves or generates a verified company profile.
    - If cached and fresh (within 7-day TTL), serves from database instantly.
    - If missing or forced, executes autonomous LangGraph profiling pipeline.
    """
    is_valid, clean_nr = validate_org_number(orgnr)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Norwegian organization number: {clean_nr}",
        )

    # 1. Check cache in database if not forced
    if not force:
        with Session(engine) as session:
            if is_profile_fresh(clean_nr, session, max_age_days=settings.cache_ttl_days_registry):
                stored = get_profile_by_orgnr(clean_nr, session)
                if stored:
                    stored.run_metadata.cached = True
                    return stored

    # 2. Execute live agent workflow
    try:
        agent = SignalpostAgent()
        profile = await agent.run(clean_nr)

        # 3. Persist to SQLite and detect diffs
        with Session(engine) as session:
            save_or_update_profile(profile, session)

        # 4. Async sync to Supabase if configured
        if supabase_sync.is_configured:
            asyncio.create_task(supabase_sync.sync_profile(profile))

        return profile

    except Exception as e:  # noqa: BLE001
        logger.error(f"Error profiling company {clean_nr}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/company/{orgnr}/history")
def get_company_diff_history(orgnr: str):
    """Returns the full audit log and field-level diff history for an organization."""
    is_valid, clean_nr = validate_org_number(orgnr)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid organization number: {clean_nr}")

    with Session(engine) as session:
        history = get_profile_history(clean_nr, session)
        return {
            "org_number": clean_nr,
            "revision_count": len(history),
            "revisions": [
                {
                    "id": h.id,
                    "revision_ref": h.revision_ref,
                    "changed_at": h.changed_at,
                    "change_reason": h.change_reason,
                    "field_name": h.field_name,
                    "old_value": h.old_value,
                    "new_value": h.new_value,
                }
                for h in history
            ],
        }


@app.get("/api/companies")
def list_companies(
    search: str | None = None,
    status: str | None = None,
    municipality: str | None = None,
    tracked_only: bool = False,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="last_checked_at"),
    sort_order: str = Query(default="desc"),
):
    """Returns paginated, searchable, and filterable list of all indexed companies."""
    with Session(engine) as session:
        query = select(CompanyProfileModel)

        if search:
            s_clean = f"%{search.strip()}%"
            query = query.where(
                (CompanyProfileModel.legal_name.ilike(s_clean))
                | (CompanyProfileModel.org_number.like(s_clean))
            )
        if status:
            query = query.where(CompanyProfileModel.status == status.upper())
        if municipality:
            query = query.where(CompanyProfileModel.municipality.ilike(f"%{municipality.strip()}%"))
        if tracked_only:
            query = query.where(CompanyProfileModel.is_tracked.is_(True))

        # Total count
        count_query = select(func.count()).select_from(query.subquery())
        total_items = session.exec(count_query).one()

        # Sorting
        sort_col = getattr(CompanyProfileModel, sort_by, CompanyProfileModel.last_checked_at)
        if sort_order.lower() == "asc":
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())

        # Pagination
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)
        rows = session.exec(query).all()

        items = [
            {
                "org_number": r.org_number,
                "legal_name": r.legal_name,
                "status": r.status,
                "org_form": r.org_form,
                "municipality": r.municipality,
                "employees": r.employees,
                "facts_count": r.facts_count,
                "is_tracked": r.is_tracked,
                "last_checked_at": r.last_checked_at,
            }
            for r in rows
        ]

        total_pages = (total_items + size - 1) // size if total_items > 0 else 1
        return {
            "items": items,
            "total": total_items,
            "page": page,
            "size": size,
            "pages": total_pages,
        }


@app.get("/api/companies/search")
async def search_companies_by_name(q: str = Query(..., min_length=2, description="Search query")):
    """Searches official Brønnøysundregistrene Enhetsregisteret by company name."""
    connector = BrregEnheterConnector()
    async with httpx.AsyncClient() as client:
        results = await connector.search_entities(client, q)
    return {"query": q, "results": results, "count": len(results)}


@app.get("/api/companies/{orgnr}/preview")
async def preview_company(orgnr: str):
    """Previews verified company identity and checks existing database state."""
    is_valid, clean_nr = validate_org_number(orgnr)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid Norwegian organization number")

    with Session(engine) as session:
        stored = session.exec(
            select(CompanyProfileModel).where(CompanyProfileModel.org_number == clean_nr)
        ).first()
        if stored:
            return {
                "org_number": clean_nr,
                "legal_name": stored.legal_name,
                "status": stored.status,
                "org_form": stored.org_form,
                "address": stored.address,
                "municipality": stored.municipality,
                "is_already_profiled": True,
                "is_tracked": stored.is_tracked,
                "facts_count": stored.facts_count,
                "last_checked_at": stored.last_checked_at,
            }

    connector = BrregEnheterConnector()
    async with httpx.AsyncClient() as client:
        entity, _ = await connector.fetch_entity(client, clean_nr)

    if not entity:
        raise HTTPException(status_code=404, detail="Organization not found in Enhetsregisteret")

    raw_name = entity.get("navn", "")
    legal_name = " ".join(raw_name) if isinstance(raw_name, list) else str(raw_name or "").strip()
    org_form = entity.get("organisasjonsform", {}).get("kode", "")
    addr_obj = entity.get("forretningsadresse") or entity.get("postadresse") or {}
    addr_parts = addr_obj.get("adresse", [])
    addr_str = ", ".join(addr_parts) if isinstance(addr_parts, list) else str(addr_parts)
    is_bankrupt = bool(entity.get("konkurs", False))

    return {
        "org_number": clean_nr,
        "legal_name": legal_name,
        "status": "BANKRUPT" if is_bankrupt else "ACTIVE",
        "org_form": org_form,
        "address": addr_str,
        "municipality": addr_obj.get("kommune") or addr_obj.get("poststed"),
        "is_already_profiled": False,
        "is_tracked": False,
        "facts_count": 0,
        "last_checked_at": None,
    }


@app.post("/api/companies", response_model=CompanyProfile)
async def add_company(request: AddCompanyRequest):
    """Profiles a company and automatically adds it to the tracked watchlist."""
    is_valid, clean_nr = validate_org_number(request.org_number)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid Norwegian organization number")

    if not request.force_refresh:
        with Session(engine) as session:
            if is_profile_fresh(clean_nr, session, max_age_days=settings.cache_ttl_days_registry):
                stored = get_profile_by_orgnr(clean_nr, session)
                if stored:
                    if request.track:
                        model = session.exec(
                            select(CompanyProfileModel).where(CompanyProfileModel.org_number == clean_nr)
                        ).first()
                        if model and not model.is_tracked:
                            model.is_tracked = True
                            session.add(model)
                            session.commit()
                    stored.run_metadata.cached = True
                    return stored

    try:
        agent = SignalpostAgent()
        profile = await agent.run(clean_nr)
        profile.is_tracked = request.track

        with Session(engine) as session:
            save_or_update_profile(profile, session)

        if supabase_sync.is_configured:
            asyncio.create_task(supabase_sync.sync_profile(profile))

        return profile
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to add company {clean_nr}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/companies/bulk")
async def add_companies_bulk(request: BulkAddCompaniesRequest, background_tasks: BackgroundTasks):
    """Queues bulk company additions with automatic watchlist tracking."""
    valid_numbers: list[str] = []
    for num in request.org_numbers:
        is_val, clean = validate_org_number(num)
        if is_val and clean not in valid_numbers:
            valid_numbers.append(clean)

    if not valid_numbers:
        raise HTTPException(status_code=400, detail="No valid organization numbers provided")

    run_id = f"bulk_{uuid.uuid4().hex[:8]}"
    ACTIVE_RUNS[run_id] = {
        "run_id": run_id,
        "status": "QUEUED",
        "total_companies": len(valid_numbers),
        "processed_count": 0,
        "successful_count": 0,
        "cached_count": 0,
        "failed_count": 0,
        "progress_pct": 0.0,
        "results": [],
    }

    background_tasks.add_task(
        _run_batch_worker, run_id, valid_numbers, request.concurrency, request.force_refresh
    )
    return {
        "run_id": run_id,
        "total": len(valid_numbers),
        "message": f"Bulk profiling queued for {len(valid_numbers)} companies",
    }


@app.patch("/api/companies/{orgnr}/track")
def toggle_company_track(orgnr: str):
    """Toggles watchlist tracking status for a company."""
    is_valid, clean_nr = validate_org_number(orgnr)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid Norwegian organization number")

    with Session(engine) as session:
        model = session.exec(
            select(CompanyProfileModel).where(CompanyProfileModel.org_number == clean_nr)
        ).first()
        if not model:
            raise HTTPException(status_code=404, detail="Company not found in local database")
        model.is_tracked = not model.is_tracked
        session.add(model)
        session.commit()
        return {"org_number": clean_nr, "is_tracked": model.is_tracked}



async def _run_batch_worker(run_id: str, org_numbers: list[str], concurrency: int, force: bool):
    """Background task executing the batch run with live event emission."""
    state = ACTIVE_RUNS[run_id]
    state["status"] = "RUNNING"
    state["started_at"] = datetime.now(UTC).isoformat()
    start_time = time.time()

    semaphore = asyncio.Semaphore(concurrency)
    agent = SignalpostAgent()

    async def _worker(nr: str):
        if state["status"] == "CANCELLED":
            return None

        async with semaphore:
            state["current_orgnr"] = nr
            try:
                # Check DB cache
                if not force:
                    with Session(engine) as session:
                        if is_profile_fresh(nr, session):
                            cached_profile = get_profile_by_orgnr(nr, session)
                            if cached_profile:
                                state["cached_count"] += 1
                                state["processed_count"] += 1
                                state["results"].append(
                                    {
                                        "org_number": cached_profile.org_number,
                                        "legal_name": cached_profile.legal_name,
                                        "status": cached_profile.status,
                                        "cached": True,
                                    }
                                )
                                return cached_profile

                profile = await agent.run(nr)
                with Session(engine) as session:
                    save_or_update_profile(profile, session)

                if supabase_sync.is_configured:
                    await supabase_sync.sync_profile(profile)

                state["successful_count"] += 1
                state["results"].append(
                    {
                        "org_number": profile.org_number,
                        "legal_name": profile.legal_name,
                        "status": profile.status,
                        "cached": False,
                    }
                )

            except Exception as e:  # noqa: BLE001
                logger.error(f"Batch task failed for {nr}: {e}")
                state["failed_count"] += 1
            finally:
                state["processed_count"] += 1
                state["progress_pct"] = round(
                    (state["processed_count"] / state["total_companies"]) * 100, 1
                )

    await asyncio.gather(*[_worker(nr) for nr in org_numbers])

    duration = time.time() - start_time
    state["status"] = "COMPLETED"
    state["completed_at"] = datetime.now(UTC).isoformat()
    state["duration_seconds"] = round(duration, 2)


@app.post("/api/run")
async def start_batch_run(
    request: BatchRunRequest,
    background_tasks: BackgroundTasks,
):
    """Initiates an asynchronous batch profiling execution across a list of org numbers."""
    valid_numbers: list[str] = []
    for num in request.org_numbers:
        is_val, clean = validate_org_number(num)
        if is_val and clean not in valid_numbers:
            valid_numbers.append(clean)

    if not valid_numbers:
        raise HTTPException(
            status_code=400,
            detail="No valid 9-digit Norwegian organization numbers provided",
        )

    run_id = f"run_{uuid.uuid4().hex[:12]}"
    run_state = {
        "run_id": run_id,
        "status": "QUEUED",
        "total_companies": len(valid_numbers),
        "processed_count": 0,
        "successful_count": 0,
        "cached_count": 0,
        "failed_count": 0,
        "progress_pct": 0.0,
        "current_orgnr": None,
        "results": [],
    }
    ACTIVE_RUNS[run_id] = run_state

    background_tasks.add_task(
        _run_batch_worker,
        run_id,
        valid_numbers,
        request.concurrency,
        request.force_refresh,
    )

    return {
        "run_id": run_id,
        "status": "QUEUED",
        "total_companies": len(valid_numbers),
        "stream_url": f"/api/runs/{run_id}",
    }


@app.get("/api/runs/{run_id}")
async def get_run_status_or_stream(run_id: str, stream: bool = Query(default=True)):
    """
    Returns run status or live SSE event stream.
    When stream=true, sends Server-Sent Events (SSE) progress updates.
    """
    if run_id not in ACTIVE_RUNS:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    if not stream:
        return ACTIVE_RUNS[run_id]

    async def event_generator():
        while True:
            state = ACTIVE_RUNS.get(run_id)
            if not state:
                break

            data = json.dumps(state)
            yield f"data: {data}\n\n"

            if state.get("status") in ["COMPLETED", "FAILED", "CANCELLED"]:
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/reports/quality")
def get_latest_quality_report():
    """Returns the latest batch quality report if generated."""
    report_file = settings.out_dir / "quality_report.json"
    if not report_file.exists():
        return {"report_exists": False, "message": "No batch run has been executed yet."}

    try:
        with open(report_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"report_exists": True, "report": data}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to read report: {e}")


# Static frontend mounting (Vite SPA)
FRONTEND_DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"
if FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="API route not found")
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")

