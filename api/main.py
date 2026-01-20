"""FastAPI server for Kompline compliance analysis."""

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from kompline.runner import KomplineRunner
from kompline.guardrails.input_validator import validate_python_source
from kompline.tracing.logger import get_tracer

app = FastAPI(
    title="Kompline API",
    description="Multi-agent continuous compliance system for Korean financial regulations",
    version="0.1.0",
)

# Global runner instance
runner: KomplineRunner | None = None
last_pending_reviews: list[dict[str, Any]] = []


def get_runner() -> KomplineRunner:
    """Get or create the global runner instance."""
    global runner
    if runner is None:
        runner = KomplineRunner()
    return runner


class AnalyzeRequest(BaseModel):
    """Request body for code analysis."""

    source_code: str | None = None
    artifact_path: str | None = None
    compliance_ids: list[str] | None = None
    use_llm: bool = True
    require_review: bool = True


class AnalyzeResponse(BaseModel):
    """Response body for code analysis."""

    success: bool
    result: dict[str, Any] | None = None
    report: dict[str, Any] | None = None
    report_markdown: str | None = None
    pending_reviews: list[dict[str, Any]] = []
    trace: list[dict[str, Any]] = []
    error: str | None = None



@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "kompline"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_code(request: AnalyzeRequest):
    """Analyze source code for compliance.

    Args:
        request: The analysis request containing source code.

    Returns:
        Analysis results including report and any pending reviews.
    """
    # Validate input first (source_code only)
    if request.source_code:
        validation = validate_python_source(request.source_code)
        if not validation.valid:
            raise HTTPException(
                status_code=400,
                detail={"errors": validation.errors},
            )
    if not request.source_code and not request.artifact_path:
        raise HTTPException(
            status_code=400,
            detail={"error": "Either source_code or artifact_path is required"},
        )

    # Run analysis
    try:
        result = await get_runner().analyze(
            source_code=request.source_code,
            artifact_path=request.artifact_path,
            compliance_ids=request.compliance_ids,
            use_llm=request.use_llm,
            require_review=request.require_review,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": str(e)},
        )

    # Get pending reviews from the result
    pending_ids: list[str] = []
    pending_reviews: list[dict[str, Any]] = []
    result_payload = result.get("result") if isinstance(result, dict) else None
    if result_payload:
        for rel in result_payload.get("relations", []):
            for finding in rel.get("findings", []):
                if finding.get("requires_human_review"):
                    pending_ids.append(finding.get("id", ""))
                    pending_reviews.append(finding)
    global last_pending_reviews
    last_pending_reviews = pending_reviews

    # Get trace
    trace = get_runner().get_trace()

    return AnalyzeResponse(
        success=result.get("success", False),
        result=result.get("result"),
        report=result.get("report"),
        report_markdown=result.get("report_markdown"),
        pending_reviews=pending_reviews,
        trace=trace,
        error=result.get("error"),
    )


@app.get("/reviews")
async def get_pending_reviews():
    """Get pending reviews from the last analysis run."""
    return {"pending": last_pending_reviews}


@app.get("/trace")
async def get_trace():
    """Get the event trace from the current session."""
    return {"events": get_tracer().get_events()}


@app.delete("/trace")
async def clear_trace():
    """Clear the event trace."""
    get_tracer().clear()
    return {"status": "cleared"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8888)
