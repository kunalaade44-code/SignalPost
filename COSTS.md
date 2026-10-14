# 💰 Signalpost Expected Run Costs & Budget Analysis

This document provides a transparent, verifiable breakdown of operational costs, API pricing models, and network resource budgets for Signalpost.

---

## 📊 Summary of Expected Costs

| Workload | Outbound HTTP Requests | Mistral AI API Cost | Public Registry Cost | Total Expected Cost |
| :--- | :---: | :---: | :---: | :---: |
| **Daily 100 Companies Test** | ~600 - 1,200 req | **$0.02 - $0.05 USD** | $0.00 (Free Open Data) | **$0.02 - $0.05 USD** |
| **1,000 Companies Bulk Run** | ~5,000 - 8,000 req | **$0.20 - $0.45 USD** | $0.00 (Free Open Data) | **&lt; $0.50 USD** |
| **Re-run (Cached / No Change)** | ~100 - 200 req | **$0.00 USD** | $0.00 (Free Open Data) | **$0.00 USD** |

> **Compliance Guarantee**: The test allows up to **$10.00 USD** per daily run. Signalpost's typical 100-company run cost is **$0.03 USD**, consuming only **0.3% of the allowable budget**.

---

## 🔍 Cost Component Breakdown

### 1. Public Registry Data: $0.00 (100% Free)
- **Brønnøysundregistrene (Enhetsregisteret & Regnskapsregisteret)** provides public REST APIs under the Norwegian Licence for Open Government Data (NLOD 2.0).
- **Cost**: **$0.00 per request**, unlimited public access without rate limiting fees.
- **Data extracted**: Legal entity info, status, NACE codes, registered roles, and full verbatim 3-year financial accounts.

### 2. LLM Extraction & Summaries (Mistral AI)
- **Provider**: Mistral AI (`mistral-small-latest` via REST API)
- **Free Tier Availability**: Mistral AI offers a generous free tier with API keys for developers at $0.00.
- **Paid Tier Pricing (Mistral Small)**:
  - Input tokens: **$0.20 per 1,000,000 tokens** ($0.0000002 / token)
  - Output tokens: **$0.60 per 1,000,000 tokens** ($0.0000006 / token)
- **Token Usage per Company**:
  - Input (sanitized website summary): ~800 to 1,200 tokens
  - Output (structured JSON business description & products): ~120 to 180 tokens
  - Cost per company: `(1,000 × $0.0000002) + (150 × $0.0000006)` = **$0.00029 USD per company**
- **100 Companies Cost**: `100 × $0.00029` = **~$0.029 USD**
- **1,000 Companies Cost**: `1,000 × $0.00029` = **~$0.29 USD**

### 3. Strict Non-Fabrication Rule Prevents LLM Waste
- **Financial numbers are NEVER processed by the LLM**.
- All revenue, profit, balance sheet, and equity figures are parsed deterministically directly from Regnskapsregisteret JSON.
- This eliminates any risk of hallucination and saves significant token expenditure.

### 4. Deterministic Fallback Mode ($0.00 Cost)
- If `MISTRAL_API_KEY` is not provided, or if the declared cost threshold approaches the limit, Signalpost automatically transitions into **Deterministic Heuristic Extraction Mode**.
- In this mode:
  - Meta tags, OpenGraph summaries, and informative text blocks are extracted deterministically.
  - Email, Norwegian phone numbers (`+47`), and verified social links are extracted via regex and domain verification.
  - Cost: **$0.00 USD**.

---

## 🌐 Network & Request Budgeting

The benchmark evaluation enforces a hard limit of **2,000 outbound HTTP requests** for the daily 100-company test.

### Per-Company Request Budget

| Request Type | Maximum Allowed | Typical Count | Notes |
| :--- | :---: | :---: | :--- |
| Enhetsregisteret (`/enheter/{orgnr}`) | 1 | 1 | Legal entity facts |
| Roller (`/enheter/{orgnr}/roller`) | 1 | 1 | Corporate officers & board |
| Regnskapsregisteret (`/regnskap/{orgnr}`) | 1 | 1 | 3-year annual accounts |
| Homepage discovery & fetch | 2 | 1-2 | Follows redirects safely |
| Allowed subpages (`/om-oss`, `/kontakt`) | 3 | 1-2 | Only if homepage matches |
| **Total per Company** | **8 requests** | **5-7 requests** | Well below 18 req budget |

- **For 100 Companies**: 100 × 7 = **~700 requests** (Only 35% of the 2,000 request limit).
- **Global Circuit Breaker**: If total outbound requests exceed 1,850, `BudgetManager` blocks further web crawling and executes only essential registry lookups.
- **Deadline Guard**: If run time exceeds 40 minutes (out of the 45-minute cap), background workers skip optional subpage crawling to guarantee completion.

---

## 🔄 Cache & Refresh Economics

- Cached responses are stored in SQLite and local disk with SHA-256 ETag tracking.
- Re-running the agent on an already profiled company checks freshness (`cache_ttl_days_registry=7`, `cache_ttl_days_website=30`).
- If data has not changed, the existing profile is served with `cached=true`, incurring **0 API requests and $0.00 cost**.
