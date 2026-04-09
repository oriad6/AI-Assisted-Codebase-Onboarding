from fastapi import APIRouter, Depends, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from services.github import fetch_github_repo
from services.ai import generate_content_with_fallback, split_analysis

router = APIRouter(prefix="/api", tags=["analyze"])


class GithubAnalyzeRequest(BaseModel):
    url: str
    api_key: str | None = None  # Optional — if provided, runs AI analysis too


class FetchResponse(BaseModel):
    success: bool
    error: str | None = None
    files: list[dict] | None = None
    code_context: str | None = None


class AnalysisResponse(BaseModel):
    success: bool
    error: str | None = None
    analysis_module: str = ""
    analysis_risk: str = ""
    model_used: str = ""


@router.post("/fetch-github", response_model=FetchResponse)
def fetch_github(req: GithubAnalyzeRequest):
    """Fetch files from a GitHub repo. Does NOT run AI analysis."""
    files, err = fetch_github_repo(req.url)
    if err:
        return FetchResponse(success=False, error=err)
    code_context = "".join(
        [f"\n--- {f['name']} ---\n{f['content']}" for f in files]
    )
    return FetchResponse(success=True, files=files, code_context=code_context)


@router.post("/upload-files", response_model=FetchResponse)
async def upload_files(files: list[UploadFile] = File(...)):
    """Process uploaded code files."""
    files_data = []
    for f in files:
        try:
            content = (await f.read()).decode("utf-8")
            files_data.append({
                "name": f.filename,
                "content": content,
                "size": len(content),
            })
        except Exception:
            pass
    if not files_data:
        return FetchResponse(success=False, error="No valid text files.")
    code_context = "".join(
        [f"\n--- {f['name']} ---\n{f['content']}" for f in files_data]
    )
    return FetchResponse(success=True, files=files_data, code_context=code_context)


class RunAnalysisRequest(BaseModel):
    code_context: str
    api_key: str


@router.post("/analyze", response_model=AnalysisResponse)
def run_analysis(req: RunAnalysisRequest):
    """Run AI analysis on already-fetched code context."""
    prompt = (
        "Analyze this code. Provide two clear sections: "
        "1. MODULE ANALYSIS (Architecture overview) and "
        "2. RISK MAP (Potential vulnerabilities/risks). "
        "Separate them strictly with the token '<<<SEP>>>'.\n"
        + req.code_context[:25000]
    )
    res, model_name = generate_content_with_fallback(prompt, req.api_key)
    if model_name == "Error":
        return AnalysisResponse(success=False, error=res)

    mod_text, risk_text = split_analysis(res)
    return AnalysisResponse(
        success=True,
        analysis_module=mod_text,
        analysis_risk=risk_text,
        model_used=model_name,
    )
