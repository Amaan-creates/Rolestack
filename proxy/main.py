"""
Rolestack Job Search Proxy
==========================
Python/FastAPI server that runs jobspy server-side to scrape
LinkedIn and Indeed without CORS restrictions.

Deploy: Render (free tier) or Railway ($5/month)
Endpoint: POST /search
Auth: PROXY_SECRET env var (checked against X-Proxy-Secret header)
"""

from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

app = FastAPI(title="Rolestack Job Proxy", version="1.0.0")

# Allow requests from Supabase Edge Functions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

PROXY_SECRET = os.getenv("PROXY_SECRET", "rs_proxy_dev_secret")
executor = ThreadPoolExecutor(max_workers=4)


class SearchRequest(BaseModel):
    q: str = "Account Executive"
    location: str = "London, UK"
    sites: list[str] = ["linkedin", "indeed"]
    results: int = 15
    hours_old: Optional[int] = 72


def run_jobspy_sync(q: str, location: str, sites: list[str], results: int, hours_old: int):
    """Run jobspy synchronously (runs in thread pool to avoid blocking)"""
    try:
        from jobspy import scrape_jobs
        import pandas as pd

        jobs_df = scrape_jobs(
            site_name=sites,
            search_term=q,
            location=location,
            results_wanted=results,
            hours_old=hours_old,
            country_indeed="UK",
            linkedin_fetch_description=False,  # faster, no rate limit
            verbose=0,
        )

        if jobs_df is None or jobs_df.empty:
            return []

        jobs = []
        for _, row in jobs_df.iterrows():
            # Normalise salary
            salary = ""
            if pd.notna(row.get("min_amount")) and pd.notna(row.get("max_amount")):
                mn = int(row["min_amount"])
                mx = int(row["max_amount"])
                currency = row.get("currency", "£") or "£"
                interval = row.get("interval", "yearly") or "yearly"
                if interval == "yearly":
                    salary = f"£{mn//1000}k–£{mx//1000}k"
                elif interval == "monthly":
                    salary = f"£{mn:,}–£{mx:,}/mo"
                else:
                    salary = f"{currency}{mn}–{currency}{mx}"

            jobs.append({
                "source": str(row.get("site", "unknown")).lower(),
                "company": str(row.get("company", "")) or "",
                "title": str(row.get("title", "")) or "",
                "description": (str(row.get("description", "")) or "")[:200],
                "salary": salary,
                "salaryNum": int(row["max_amount"]) if pd.notna(row.get("max_amount")) else 0,
                "location": str(row.get("location", location)) or location,
                "url": str(row.get("job_url", "")) or "",
                "market": "uk",
                "sponsorStatus": None,
                "postedAt": str(row.get("date_posted", "")) or "",
            })

        return jobs

    except ImportError:
        raise RuntimeError("jobspy not installed. Run: pip install python-jobspy")
    except Exception as e:
        raise RuntimeError(f"jobspy error: {str(e)}")


@app.get("/health")
async def health():
    """Health check — also used as warm-up ping"""
    return {"status": "ok", "service": "rolestack-proxy"}


@app.get("/wake")
async def wake():
    """Warm-up endpoint — Edge Function pings this 3s before search"""
    return {"status": "awake"}


@app.post("/search")
async def search(
    body: SearchRequest,
    x_proxy_secret: Optional[str] = Header(None),
):
    """
    Main search endpoint.
    Called by Supabase Edge Function job-search.
    """
    # Auth check
    if x_proxy_secret != PROXY_SECRET:
        raise HTTPException(status_code=401, detail="Invalid proxy secret")

    # Validate sites
    valid_sites = {"linkedin", "indeed", "glassdoor"}
    sites = [s for s in body.sites if s in valid_sites]
    if not sites:
        sites = ["linkedin", "indeed"]

    try:
        loop = asyncio.get_event_loop()
        jobs = await loop.run_in_executor(
            executor,
            run_jobspy_sync,
            body.q,
            body.location,
            sites,
            min(body.results, 20),  # cap at 20 to avoid rate limits
            body.hours_old or 72,
        )

        source_counts = {}
        for j in jobs:
            src = j["source"]
            source_counts[src] = source_counts.get(src, 0) + 1

        return {
            "jobs": jobs,
            "total": len(jobs),
            "sources": source_counts,
        }

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
