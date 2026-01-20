"""FastAPI server for Kompline compliance analysis."""

import uuid
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from kompline.runner import KomplineRunner
from kompline.guardrails.input_validator import validate_python_source
from kompline.tracing.logger import get_tracer
from kompline.persistence import load_registries_from_db
from kompline.registry import get_compliance_registry, get_artifact_registry
from config.settings import settings

app = FastAPI(
    title="Kompline API",
    description="Multi-agent continuous compliance system for Korean financial regulations",
    version="0.1.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:4000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
runner: KomplineRunner | None = None
audits_store: dict[str, dict[str, Any]] = {}
reviews_store: dict[str, dict[str, Any]] = {}


def get_runner() -> KomplineRunner:
    """Get or create the global runner instance."""
    global runner
    if runner is None:
        runner = KomplineRunner()
    return runner


async def ensure_registries_loaded(require_db: bool = False) -> None:
    """Ensure compliance/artifact registries are loaded from DB."""
    if not settings.database_url:
        if require_db:
            raise HTTPException(status_code=500, detail="DATABASE_URL is not set")
        return
    await load_registries_from_db()


# ============ Models ============

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
    audit_id: str | None = None
    audit_run_id: str | None = None
    result: dict[str, Any] | None = None
    report: dict[str, Any] | None = None
    report_markdown: str | None = None
    pending_reviews: list[dict[str, Any]] = []
    trace: list[dict[str, Any]] = []
    error: str | None = None


class AuditSummary(BaseModel):
    """Summary of an audit."""
    id: str
    name: str
    status: str
    compliance_ids: list[str]
    created_at: str
    completed_at: str | None = None
    is_compliant: bool | None = None
    total_passed: int = 0
    total_failed: int = 0
    total_review: int = 0


class ReviewAction(BaseModel):
    """Action on a review."""
    comment: str | None = None


class AuditRequestCreate(BaseModel):
    """Request to create a new audit request."""
    name: str
    description: str | None = None
    compliance_ids: list[str]
    use_llm: bool = True
    require_review: bool = True


class AuditFileInfo(BaseModel):
    """Information about an uploaded file."""
    id: str
    filename: str
    file_type: str
    size: int
    uploaded_at: str


class AuditRequestResponse(BaseModel):
    """Response for an audit request."""
    id: str
    name: str
    description: str | None
    status: str
    compliance_ids: list[str]
    files: list[AuditFileInfo]
    created_at: str
    submitted_at: str | None = None
    completed_at: str | None = None
    result: dict[str, Any] | None = None
    is_compliant: bool | None = None
    total_passed: int = 0
    total_failed: int = 0
    total_review: int = 0


# Audit requests storage (in-memory for demo)
audit_requests_store: dict[str, dict[str, Any]] = {}


# ============ Health Check ============

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "kompline"}


# ============ Audits ============

@app.get("/api/audits")
async def list_audits(
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    """List all audits with optional filtering."""
    audits = list(audits_store.values())

    # Filter by status
    if status:
        audits = [a for a in audits if a.get("status") == status]

    # Sort by created_at descending
    audits.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    # Pagination
    total = len(audits)
    audits = audits[offset:offset + limit]

    return {
        "audits": audits,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@app.post("/api/audits", response_model=AnalyzeResponse)
async def create_audit(request: AnalyzeRequest):
    """Create and run a new audit."""
    # Validate input
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

    resolved_compliance_ids = request.compliance_ids
    if not resolved_compliance_ids:
        await ensure_registries_loaded(require_db=True)
        resolved_compliance_ids = get_compliance_registry().list_ids()
        if not resolved_compliance_ids:
            raise HTTPException(
                status_code=400,
                detail={"error": "No compliances loaded from DB. Seed compliances or pass compliance_ids."},
            )

    # Create audit record
    audit_id = str(uuid.uuid4())[:8]
    audit_record = {
        "id": audit_id,
        "name": request.artifact_path or f"inline-code-{audit_id}",
        "status": "running",
        "compliance_ids": resolved_compliance_ids,
        "created_at": datetime.now().isoformat(),
        "source_code": request.source_code,
    }
    audits_store[audit_id] = audit_record

    # Run analysis
    try:
        result = await get_runner().analyze(
            source_code=request.source_code,
            artifact_path=request.artifact_path,
            compliance_ids=resolved_compliance_ids,
            use_llm=request.use_llm,
            require_review=request.require_review,
        )

        # Update audit record
        audit_record["status"] = "completed" if result.get("success") else "failed"
        audit_record["completed_at"] = datetime.now().isoformat()
        audit_record["result"] = result.get("result")
        audit_record["report_markdown"] = result.get("report_markdown")
        audit_record["audit_run_id"] = result.get("audit_run_id")

        result_payload = result.get("result", {})
        audit_record["is_compliant"] = result_payload.get("is_compliant", False)
        audit_record["total_passed"] = result_payload.get("total_passed", 0)
        audit_record["total_failed"] = result_payload.get("total_failed", 0)
        audit_record["total_review"] = result_payload.get("total_review", 0)

        # Extract pending reviews
        pending_reviews: list[dict[str, Any]] = []
        for rel in result_payload.get("relations", []):
            for finding in rel.get("findings", []):
                if finding.get("requires_human_review"):
                    finding["audit_id"] = audit_id
                    reviews_store[finding.get("id", str(uuid.uuid4()))] = finding
                    pending_reviews.append(finding)

        # Get trace
        trace = get_runner().get_trace()
        audit_record["trace"] = trace

        return AnalyzeResponse(
            success=result.get("success", False),
            audit_id=audit_id,
            audit_run_id=result.get("audit_run_id"),
            result=result.get("result"),
            report=result.get("report"),
            report_markdown=result.get("report_markdown"),
            pending_reviews=pending_reviews,
            trace=trace,
            error=result.get("error"),
        )

    except Exception as e:
        audit_record["status"] = "failed"
        audit_record["error"] = str(e)
        raise HTTPException(
            status_code=500,
            detail={"error": str(e)},
        )


@app.get("/api/audits/{audit_id}")
async def get_audit(audit_id: str):
    """Get a specific audit by ID."""
    audit = audits_store.get(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    return audit


@app.get("/api/audits/{audit_id}/logs")
async def get_audit_logs(audit_id: str, offset: int = 0, limit: int = 100):
    """Get logs for a specific audit."""
    audit = audits_store.get(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    trace = audit.get("trace", [])
    total = len(trace)
    logs = trace[offset:offset + limit]

    return {
        "logs": logs,
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + limit < total,
    }


@app.delete("/api/audits/{audit_id}")
async def delete_audit(audit_id: str):
    """Delete/cancel an audit."""
    if audit_id not in audits_store:
        raise HTTPException(status_code=404, detail="Audit not found")

    del audits_store[audit_id]
    return {"status": "deleted"}


# ============ Audit Requests (Multi-file) ============

@app.get("/api/audit-requests")
async def list_audit_requests(
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    """List all audit requests."""
    requests = list(audit_requests_store.values())

    if status:
        requests = [r for r in requests if r.get("status") == status]

    requests.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    total = len(requests)
    requests = requests[offset:offset + limit]

    return {
        "audit_requests": requests,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@app.post("/api/audit-requests")
async def create_audit_request(request: AuditRequestCreate):
    """Create a new audit request (without running yet)."""
    request_id = str(uuid.uuid4())[:8]

    audit_request = {
        "id": request_id,
        "name": request.name,
        "description": request.description,
        "status": "draft",  # draft -> pending -> running -> completed/failed
        "compliance_ids": request.compliance_ids,
        "use_llm": request.use_llm,
        "require_review": request.require_review,
        "files": [],
        "created_at": datetime.now().isoformat(),
        "submitted_at": None,
        "completed_at": None,
        "result": None,
        "is_compliant": None,
        "total_passed": 0,
        "total_failed": 0,
        "total_review": 0,
    }

    audit_requests_store[request_id] = audit_request

    return audit_request


@app.get("/api/audit-requests/{request_id}")
async def get_audit_request(request_id: str):
    """Get an audit request by ID."""
    audit_request = audit_requests_store.get(request_id)
    if not audit_request:
        raise HTTPException(status_code=404, detail="Audit request not found")
    return audit_request


@app.post("/api/audit-requests/{request_id}/files")
async def upload_audit_file(
    request_id: str,
    file: UploadFile = File(...),
):
    """Upload a file to an audit request."""
    audit_request = audit_requests_store.get(request_id)
    if not audit_request:
        raise HTTPException(status_code=404, detail="Audit request not found")

    if audit_request["status"] not in ["draft", "pending"]:
        raise HTTPException(status_code=400, detail="Cannot add files after submission")

    # Read file content
    content = await file.read()
    file_id = str(uuid.uuid4())[:8]

    # Determine file type
    filename = file.filename or "unknown"
    if filename.endswith(".py"):
        file_type = "python"
    elif filename.endswith(".pdf"):
        file_type = "pdf"
    elif filename.endswith((".yaml", ".yml")):
        file_type = "yaml"
    elif filename.endswith(".json"):
        file_type = "json"
    else:
        file_type = "text"

    file_info = {
        "id": file_id,
        "filename": filename,
        "file_type": file_type,
        "size": len(content),
        "content": content.decode("utf-8", errors="replace"),
        "uploaded_at": datetime.now().isoformat(),
    }

    audit_request["files"].append(file_info)

    # Return without content (for response)
    return {
        "id": file_id,
        "filename": filename,
        "file_type": file_type,
        "size": len(content),
        "uploaded_at": file_info["uploaded_at"],
    }


@app.delete("/api/audit-requests/{request_id}/files/{file_id}")
async def delete_audit_file(request_id: str, file_id: str):
    """Remove a file from an audit request."""
    audit_request = audit_requests_store.get(request_id)
    if not audit_request:
        raise HTTPException(status_code=404, detail="Audit request not found")

    if audit_request["status"] not in ["draft", "pending"]:
        raise HTTPException(status_code=400, detail="Cannot remove files after submission")

    original_count = len(audit_request["files"])
    audit_request["files"] = [f for f in audit_request["files"] if f["id"] != file_id]

    if len(audit_request["files"]) == original_count:
        raise HTTPException(status_code=404, detail="File not found")

    return {"status": "deleted"}


@app.post("/api/audit-requests/{request_id}/submit")
async def submit_audit_request(request_id: str):
    """Submit an audit request for processing."""
    audit_request = audit_requests_store.get(request_id)
    if not audit_request:
        raise HTTPException(status_code=404, detail="Audit request not found")

    if audit_request["status"] not in ["draft", "pending"]:
        raise HTTPException(status_code=400, detail="Audit already submitted")

    if not audit_request["files"]:
        raise HTTPException(status_code=400, detail="At least one file is required")

    audit_request["status"] = "running"
    audit_request["submitted_at"] = datetime.now().isoformat()

    # Run analysis for each file
    try:
        all_results = []
        all_traces = []
        total_passed = 0
        total_failed = 0
        total_review = 0

        for file_info in audit_request["files"]:
            if file_info["file_type"] == "python":
                result = await get_runner().analyze(
                    source_code=file_info["content"],
                    compliance_ids=audit_request["compliance_ids"],
                    use_llm=audit_request["use_llm"],
                    require_review=audit_request["require_review"],
                )

                result_payload = result.get("result", {})
                all_results.append({
                    "file_id": file_info["id"],
                    "filename": file_info["filename"],
                    "result": result_payload,
                })

                total_passed += result_payload.get("total_passed", 0)
                total_failed += result_payload.get("total_failed", 0)
                total_review += result_payload.get("total_review", 0)

                # Collect reviews
                for rel in result_payload.get("relations", []):
                    for finding in rel.get("findings", []):
                        if finding.get("requires_human_review"):
                            finding["audit_request_id"] = request_id
                            finding["file_id"] = file_info["id"]
                            reviews_store[finding.get("id", str(uuid.uuid4()))] = finding

        # Update audit request
        audit_request["status"] = "completed"
        audit_request["completed_at"] = datetime.now().isoformat()
        audit_request["result"] = {
            "file_results": all_results,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_review": total_review,
        }
        audit_request["is_compliant"] = total_failed == 0 and total_review == 0
        audit_request["total_passed"] = total_passed
        audit_request["total_failed"] = total_failed
        audit_request["total_review"] = total_review
        audit_request["trace"] = get_runner().get_trace()

        return audit_request

    except Exception as e:
        audit_request["status"] = "failed"
        audit_request["error"] = str(e)
        raise HTTPException(status_code=500, detail={"error": str(e)})


@app.delete("/api/audit-requests/{request_id}")
async def delete_audit_request(request_id: str):
    """Delete an audit request."""
    if request_id not in audit_requests_store:
        raise HTTPException(status_code=404, detail="Audit request not found")

    del audit_requests_store[request_id]
    return {"status": "deleted"}


# ============ Reviews (HITL) ============

@app.get("/api/reviews")
async def list_reviews(status: str | None = None):
    """Get all pending reviews."""
    reviews = list(reviews_store.values())

    if status:
        reviews = [r for r in reviews if r.get("status") == status]

    # Filter to only pending reviews
    pending = [r for r in reviews if r.get("requires_human_review", False)]

    return {"pending": pending, "total": len(pending)}


@app.get("/api/reviews/{review_id}")
async def get_review(review_id: str):
    """Get a specific review."""
    review = reviews_store.get(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@app.post("/api/reviews/{review_id}/approve")
async def approve_review(review_id: str, action: ReviewAction | None = None):
    """Approve a review."""
    review = reviews_store.get(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review["requires_human_review"] = False
    review["review_status"] = "approved"
    review["reviewed_at"] = datetime.now().isoformat()
    if action and action.comment:
        review["review_comment"] = action.comment

    return {"status": "approved", "review": review}


@app.post("/api/reviews/{review_id}/reject")
async def reject_review(review_id: str, action: ReviewAction | None = None):
    """Reject a review."""
    review = reviews_store.get(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review["requires_human_review"] = False
    review["review_status"] = "rejected"
    review["reviewed_at"] = datetime.now().isoformat()
    if action and action.comment:
        review["review_comment"] = action.comment

    return {"status": "rejected", "review": review}


@app.post("/api/reviews/{review_id}/comment")
async def add_review_comment(review_id: str, action: ReviewAction):
    """Add a comment/request context for a review."""
    review = reviews_store.get(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if not action.comment:
        raise HTTPException(status_code=400, detail="Comment is required")

    if "comments" not in review:
        review["comments"] = []
    review["comments"].append({
        "text": action.comment,
        "created_at": datetime.now().isoformat(),
    })

    return {"status": "commented", "review": review}


# ============ Metadata ============

@app.get("/api/compliances")
async def list_compliances():
    """Get available compliance frameworks."""
    await ensure_registries_loaded(require_db=True)
    registry = get_compliance_registry()
    compliances = []
    for comp in registry.list_all():
        compliances.append(
            {
                "id": comp.id,
                "name": comp.name,
                "version": comp.version,
                "jurisdiction": comp.jurisdiction,
                "scope": comp.scope,
                "description": comp.description,
                "item_count": len(comp.get_items()),
            }
        )

    return {"compliances": compliances}


@app.get("/api/artifacts")
async def list_artifacts():
    """Get available artifacts."""
    await ensure_registries_loaded(require_db=True)
    registry = get_artifact_registry()
    artifacts = []
    for art in registry.list_all():
        artifacts.append(
            {
                "id": art.id,
                "name": art.name,
                "type": art.type.value,
                "locator": art.locator,
                "description": art.description,
                "tags": art.tags,
            }
        )
    return {"artifacts": artifacts}


# ============ Reports ============

@app.get("/api/reports")
async def list_reports():
    """Get all generated reports."""
    reports = []
    for audit_id, audit in audits_store.items():
        if audit.get("status") == "completed" and audit.get("report_markdown"):
            reports.append({
                "id": audit_id,
                "audit_id": audit_id,
                "name": f"Compliance Report - {audit.get('name', 'Unknown')}",
                "compliance_ids": audit.get("compliance_ids", []),
                "created_at": audit.get("completed_at", audit.get("created_at")),
                "is_compliant": audit.get("is_compliant", False),
                "format": "Markdown",
            })

    return {"reports": reports}


@app.get("/api/reports/{report_id}")
async def get_report(report_id: str):
    """Get a specific report."""
    audit = audits_store.get(report_id)
    if not audit or not audit.get("report_markdown"):
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "id": report_id,
        "audit_id": report_id,
        "name": f"Compliance Report - {audit.get('name', 'Unknown')}",
        "compliance_ids": audit.get("compliance_ids", []),
        "created_at": audit.get("completed_at", audit.get("created_at")),
        "is_compliant": audit.get("is_compliant", False),
        "content_markdown": audit.get("report_markdown"),
        "result": audit.get("result"),
    }


@app.get("/api/reports/{report_id}/export")
async def export_report(report_id: str, format: str = "markdown"):
    """Export a report in the specified format."""
    audit = audits_store.get(report_id)
    if not audit or not audit.get("report_markdown"):
        raise HTTPException(status_code=404, detail="Report not found")

    if format == "markdown":
        return {
            "format": "markdown",
            "content": audit.get("report_markdown"),
            "filename": f"report-{report_id}.md",
        }
    elif format == "json":
        return {
            "format": "json",
            "content": audit.get("result"),
            "filename": f"report-{report_id}.json",
        }
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")


# ============ Legacy endpoints (backwards compatibility) ============

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_code_legacy(request: AnalyzeRequest):
    """Legacy analyze endpoint - redirects to /api/audits."""
    return await create_audit(request)


@app.get("/reviews")
async def get_reviews_legacy():
    """Legacy reviews endpoint."""
    result = await list_reviews()
    return {"pending": result["pending"]}


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
