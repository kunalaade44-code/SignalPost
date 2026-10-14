import argparse
import asyncio
import sys
from pathlib import Path

from signalpost.agent.graph import SignalpostAgent
from signalpost.cli.batch_runner import BatchRunner
from signalpost.cli.sample_generator import fetch_active_org_numbers
from signalpost.storage.database import Session, engine, init_db, save_or_update_profile


def main():
    parser = argparse.ArgumentParser(
        prog="signalpost",
        description="Signalpost: Autonomous Agent for Norwegian Company Profiling & Verification",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: run (Batch profiling)
    run_parser = subparsers.add_parser("run", help="Run batch profiling on an input list of org numbers")
    run_parser.add_argument("--input", "-i", type=str, default="data/orgnrs.txt", help="Path to input orgnrs file")
    run_parser.add_argument("--out", "-o", type=str, default="out", help="Output directory for profiles & reports")
    run_parser.add_argument("--concurrency", "-c", type=int, default=8, help="Number of concurrent workers (default 8)")
    run_parser.add_argument("--force", "-f", action="store_true", help="Force refresh even if profile is cached/fresh")

    # Command: single (Single company profiling)
    single_parser = subparsers.add_parser("single", help="Profile a single Norwegian organization number")
    single_parser.add_argument("--orgnr", type=str, required=True, help="9-digit organization number")
    single_parser.add_argument("--out", "-o", type=str, default="out", help="Output directory")

    # Command: sample (Fetch valid sample org numbers from Brreg)
    sample_parser = subparsers.add_parser("sample", help="Generate >= 1,000 active valid Norwegian org numbers from Brreg")
    sample_parser.add_argument("--count", "-n", type=int, default=1000, help="Number of org numbers to collect")
    sample_parser.add_argument("--out", "-o", type=str, default="data/orgnrs_1000.txt", help="Target output file")

    # Command: serve (FastAPI + Web Dashboard server)
    serve_parser = subparsers.add_parser("serve", help="Run the Signalpost web application and REST API")
    serve_parser.add_argument("--host", type=str, default="0.0.0.0", help="Bind host (default 0.0.0.0)")
    serve_parser.add_argument("--port", "-p", type=int, default=8000, help="Bind port (default 8000)")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "run":
        input_path = Path(args.input)
        out_dir = Path(args.out)
        runner = BatchRunner(
            input_path=input_path,
            out_dir=out_dir,
            concurrency=args.concurrency,
            force_refresh=args.force,
        )
        asyncio.run(runner.run())

    elif args.command == "single":
        init_db()
        agent = SignalpostAgent()
        profile = asyncio.run(agent.run(args.orgnr))

        # Save to DB
        with Session(engine) as session:
            save_or_update_profile(profile, session)

        # Output JSON
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{profile.org_number}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(profile.model_dump_json(indent=2))

        print(f"\nProfile successfully generated for {profile.legal_name} ({profile.org_number}):")
        print(f"  Status:       {profile.status}")
        print(f"  Org Form:     {profile.org_form}")
        print(f"  Employees:    {profile.employees}")
        print(f"  Verified facts: {len(profile.facts)}")
        print(f"  Saved to:     {out_file}\n")

    elif args.command == "sample":
        out_path = Path(args.out)
        asyncio.run(fetch_active_org_numbers(target_count=args.count, out_file=out_path))

    elif args.command == "serve":
        import uvicorn
        print(f"\nStarting Signalpost Web Application on http://{args.host}:{args.port}\n")
        uvicorn.run("signalpost.api.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
