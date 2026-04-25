"""
FastAPI Backend for AI Cover Letter Generator
"""

import json
import logging
import uuid
from datetime import datetime
from typing import AsyncGenerator
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

# Import core modules
from config.settings import APPLICATIONS_LOG
from core.job_parser import JobParser
from core.research_agent import CompanyResearchAgent
from core.letter_generator import CoverLetterGenerator
from core.pdf_generator import PDFGenerator
from utils.nvidia_client import NvidiaLLM
from utils.scraper import WebScraper
from utils.cache import DiskCache

app = FastAPI(title="AI Cover Letter Generator API")

# Initialize global components
llm = NvidiaLLM()
scraper = WebScraper()
cache = DiskCache()
parser = JobParser(llm, scraper)
researcher = CompanyResearchAgent(llm, scraper, cache)
generator = CoverLetterGenerator(llm)
pdf_gen = PDFGenerator()

# Helper logic to read mock DB
def _load_log() -> list:
    try:
        with open(APPLICATIONS_LOG, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

def _save_log(entries: list) -> None:
    try:
        with open(APPLICATIONS_LOG, "w") as f:
            json.dump(entries, f, indent=2, default=str)
    except OSError as exc:
        logging.error(f"Could not save application log: {exc}")

class GenerateRequest(BaseModel):
    job_text: str
    tone: str = "professional"

import asyncio

@app.post("/api/generate")
async def generate_cover_letter(req: GenerateRequest):
    """
    Expects job_text. Returns a Server-Sent Events (SSE) stream.
    Events:
    - parsing (...done)
    - research_progress (step info)
    - content (streaming text of letter)
    - done (final payload with score & PDF path)
    """

    async def event_generator() -> AsyncGenerator[dict, None]:
        # 1. Parse Job
        yield {"event": "parsing", "data": json.dumps({"message": "Parsing job details..."})}
        
        # This is blocking currently but since it's an internal tool running locally, it's fine.
        # Ideally, we would use run_in_executor for heavy sync functions in FastAPI.
        job_data = parser._extract_structured_data(req.job_text)
        if not job_data:
            yield {"event": "error", "data": json.dumps({"message": "Could not extract job data."})}
            return
            
        # Give fallback values
        if not job_data.get("company_name"):
            job_data["company_name"] = "Unknown Company"
        if not job_data.get("position_title"):
            job_data["position_title"] = "Relevant Position"
            
        yield {"event": "parsed", "data": json.dumps({"job_data": job_data})}
        await asyncio.sleep(0.1)

        # 2. Research Stream
        research_insights = None
        for step in researcher.research_company_stream(job_data):
            if step["type"] == "progress":
                yield {"event": "research_progress", "data": json.dumps(step)}
                await asyncio.sleep(0.1)
            elif step["type"] == "research_done":
                research_insights = step["insights"]
                
        if not research_insights:
            yield {"event": "error", "data": json.dumps({"message": "Research failed."})}
            return

        # 3. Load Profile
        try:
            with open("config/user_profile.json", "r") as f:
                profile = json.load(f)
        except Exception:
            profile = {}

        # 4. Generate Stream
        for chunk in generator.generate_stream(profile, job_data, research_insights, req.tone):
            if chunk["type"] == "content":
                # Only stream text
                yield {"event": "content", "data": json.dumps({"text": chunk["content"]})}
                # Add tiny sleep to allow the yielding to flow to the client smoothly
                await asyncio.sleep(0.01)
            elif chunk["type"] == "done":
                # Create PDF
                try:
                    pdf_path = pdf_gen.generate(chunk["letter"], profile, job_data)
                except Exception as e:
                    pdf_path = None
                    
                # Save to history
                entries = _load_log()
                entry = {
                    "id": str(uuid.uuid4()),
                    "company": job_data.get("company_name", "Unknown"),
                    "position": job_data.get("position_title", "Unknown"),
                    "date": datetime.now().isoformat(),
                    "quality_score": chunk["quality_score"],
                    "letter_preview": chunk["letter"][:100] + "…" if len(chunk["letter"]) > 100 else chunk["letter"],
                    "pdf_path": pdf_path,
                    "job_data": job_data,
                    "research_summary": {
                        "momentum": research_insights.get("company_momentum", ""),
                        "culture": research_insights.get("cultural_keywords", []),
                        "initiatives": research_insights.get("recent_initiatives", []),
                    },
                }
                entries.append(entry)
                _save_log(entries)
                
                final_data = {
                    "letter": chunk["letter"],
                    "quality": chunk["quality"],
                    "pdf_path": pdf_path,
                }
                yield {"event": "done", "data": json.dumps(final_data)}
        
    return EventSourceResponse(event_generator())

@app.get("/api/history")
def get_history():
    return {"history": _load_log()}

import os
# Create static dir if not exists
os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
