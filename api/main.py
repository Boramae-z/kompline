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
from kompline.persistence import (
    load_registries_from_db,
    save_audit_request,
    get_audit_request,
    list_audit_requests as db_list_audit_requests,
    delete_audit_request as db_delete_audit_request,
    save_audit_request_file,
    delete_audit_request_file as db_delete_audit_request_file,
    get_audit_request_files,
    update_audit_request_status,
)
from kompline.registry import get_compliance_registry, get_artifact_registry
from kompline.models import (
    Compliance,
    Rule,
    RuleCategory,
    RuleSeverity,
    Artifact,
    ArtifactType,
    AccessMethod,
    Provenance,
)
from config.settings import settings
from kompline.persistence.scan_store import ScanStore

# Import API schemas
from api.schemas import (
    ComplianceCreate,
    ComplianceUpdate,
    ComplianceResponse,
    ArtifactCreate,
    ArtifactUpdate,
    ArtifactResponse,
    GitHubImportRequest,
    GitHubImportResponse,
    EvidenceResponse,
    FindingResponse,
    AuditRunResponse,
    DBStatusResponse,
    DBSyncRequest,
    DBSyncResponse,
    RuleSchema,
    ProvenanceSchema,
    RuleCategoryEnum,
    RuleSeverityEnum,
    ArtifactTypeEnum,
    AccessMethodEnum,
)

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


def get_scan_store() -> ScanStore:
    """Create a ScanStore instance from settings."""
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(
            status_code=500,
            detail="Supabase not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
        )
    from supabase import create_client
    client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return ScanStore(client)


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


class CreateScanRequest(BaseModel):
    """Request to create a new compliance scan."""
    repo_url: str
    document_ids: list[str]


class ScanResponse(BaseModel):
    """Response for a scan."""
    scan_id: str
    status: str
    repo_url: str
    report_url: str | None = None
    report_markdown: str | None = None




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
async def list_audit_requests_endpoint(
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    """List all audit requests from DB."""
    await ensure_registries_loaded(require_db=True)
    requests, total = await db_list_audit_requests(status=status, limit=limit, offset=offset)

    return {
        "audit_requests": requests,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@app.post("/api/audit-requests")
async def create_audit_request_endpoint(request: AuditRequestCreate):
    """Create a new audit request (saved to DB)."""
    await ensure_registries_loaded(require_db=True)
    request_id = str(uuid.uuid4())[:8]

    await save_audit_request(
        request_id=request_id,
        name=request.name,
        description=request.description or "",
        status="draft",
        compliance_ids=request.compliance_ids,
        use_llm=request.use_llm,
        require_review=request.require_review,
    )

    audit_request = await get_audit_request(request_id)
    return audit_request


@app.get("/api/audit-requests/{request_id}")
async def get_audit_request_endpoint(request_id: str):
    """Get an audit request by ID from DB."""
    await ensure_registries_loaded(require_db=True)
    audit_request = await get_audit_request(request_id)
    if not audit_request:
        raise HTTPException(status_code=404, detail="Audit request not found")
    return audit_request


@app.post("/api/audit-requests/{request_id}/files")
async def upload_audit_file(
    request_id: str,
    file: UploadFile = File(...),
):
    """Upload a file to an audit request (saved to DB)."""
    await ensure_registries_loaded(require_db=True)
    audit_request = await get_audit_request(request_id)
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

    content_str = content.decode("utf-8", errors="replace")

    await save_audit_request_file(
        file_id=file_id,
        audit_request_id=request_id,
        filename=filename,
        file_type=file_type,
        size=len(content),
        content=content_str,
    )

    return {
        "id": file_id,
        "filename": filename,
        "file_type": file_type,
        "size": len(content),
        "uploaded_at": datetime.now().isoformat(),
    }


@app.delete("/api/audit-requests/{request_id}/files/{file_id}")
async def delete_audit_file(request_id: str, file_id: str):
    """Remove a file from an audit request."""
    await ensure_registries_loaded(require_db=True)
    audit_request = await get_audit_request(request_id)
    if not audit_request:
        raise HTTPException(status_code=404, detail="Audit request not found")

    if audit_request["status"] not in ["draft", "pending"]:
        raise HTTPException(status_code=400, detail="Cannot remove files after submission")

    deleted = await db_delete_audit_request_file(request_id, file_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")

    return {"status": "deleted"}


@app.post("/api/audit-requests/{request_id}/submit")
async def submit_audit_request_endpoint(request_id: str):
    """Submit an audit request for processing."""
    await ensure_registries_loaded(require_db=True)
    audit_request = await get_audit_request(request_id)
    if not audit_request:
        raise HTTPException(status_code=404, detail="Audit request not found")

    if audit_request["status"] not in ["draft", "pending"]:
        raise HTTPException(status_code=400, detail="Audit already submitted")

    # Get files from DB
    files = await get_audit_request_files(request_id)
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")

    # Update status to running
    submitted_at = datetime.now()
    await update_audit_request_status(
        request_id=request_id,
        status="running",
        submitted_at=submitted_at,
    )

    # Run analysis for each file
    try:
        all_results = []
        total_passed = 0
        total_failed = 0
        total_review = 0

        for file_info in files:
            if file_info["file_type"] == "python":
                result = await get_runner().analyze(
                    source_code=file_info["content"],
                    compliance_ids=audit_request["compliance_ids"],
                    use_llm=audit_request.get("use_llm", True),
                    require_review=audit_request.get("require_review", True),
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

        # Update audit request with results
        result_json = {
            "file_results": all_results,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_review": total_review,
        }

        await update_audit_request_status(
            request_id=request_id,
            status="completed",
            completed_at=datetime.now(),
            is_compliant=(total_failed == 0 and total_review == 0),
            total_passed=total_passed,
            total_failed=total_failed,
            total_review=total_review,
            result_json=result_json,
        )

        # Return updated audit request
        updated_request = await get_audit_request(request_id)
        updated_request["trace"] = get_runner().get_trace()
        return updated_request

    except Exception as e:
        await update_audit_request_status(
            request_id=request_id,
            status="failed",
            error_message=str(e),
        )
        raise HTTPException(status_code=500, detail={"error": str(e)})


@app.delete("/api/audit-requests/{request_id}")
async def delete_audit_request_endpoint(request_id: str):
    """Delete an audit request from DB."""
    await ensure_registries_loaded(require_db=True)
    deleted = await db_delete_audit_request(request_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Audit request not found")

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


# ============ Scans (Worker-based Architecture) ============


@app.post("/scans", response_model=ScanResponse, status_code=201)
async def create_scan(request: CreateScanRequest):
    """Create a new compliance scan.

    The scan will be queued for processing by the worker architecture.
    Use GET /scans/{scan_id} to check status and retrieve results.
    """
    store = get_scan_store()
    scan_id = store.create_scan(request.repo_url, request.document_ids)
    return ScanResponse(
        scan_id=scan_id,
        status="QUEUED",
        repo_url=request.repo_url,
    )


@app.get("/scans/{scan_id}", response_model=ScanResponse)
async def get_scan_status(scan_id: str):
    """Get scan status and results.

    Status values:
    - QUEUED: Waiting to be processed
    - PROCESSING: Being validated by workers
    - REPORT_GENERATING: All validations complete, generating report
    - COMPLETED: Scan finished with report available
    - FAILED: Scan failed due to an error
    """
    store = get_scan_store()
    scan = store.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return ScanResponse(
        scan_id=scan["id"],
        status=scan["status"],
        repo_url=scan["repo_url"],
        report_url=scan.get("report_url"),
        report_markdown=scan.get("report_markdown"),
    )


@app.get("/scans/{scan_id}/results")
async def get_scan_results(scan_id: str) -> list[dict[str, Any]]:
    """Get detailed results for a scan.

    Returns a list of scan results, each containing:
    - id: Result ID
    - compliance_item_id: The compliance item that was validated
    - status: PENDING, PASS, FAIL, or ERROR
    - reasoning: Explanation of the validation result
    - evidence: Code or configuration snippets that support the result
    - worker_id: ID of the worker that processed this item
    """
    store = get_scan_store()
    scan = store.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    results = store.list_scan_results(scan_id)
    return results


# ============ Helper Functions for CRUD ============


def _compliance_to_response(c: Compliance) -> ComplianceResponse:
    """Convert Compliance domain model to API response."""
    return ComplianceResponse(
        id=c.id,
        name=c.name,
        version=c.version,
        jurisdiction=c.jurisdiction,
        scope=c.scope,
        description=c.description,
        rules=[
            RuleSchema(
                id=r.id,
                title=r.title,
                description=r.description,
                category=RuleCategoryEnum(r.category.value),
                severity=RuleSeverityEnum(r.severity.value),
                check_points=r.check_points,
                pass_criteria=r.pass_criteria,
            )
            for r in c.rules
        ],
        metadata=getattr(c, "metadata", {}),
    )


def _request_to_compliance(data: ComplianceCreate) -> Compliance:
    """Convert API request to Compliance domain model."""
    return Compliance(
        id=data.id,
        name=data.name,
        version=data.version,
        jurisdiction=data.jurisdiction,
        scope=data.scope,
        description=data.description,
        rules=[
            Rule(
                id=r.id,
                title=r.title,
                description=r.description,
                category=RuleCategory(r.category.value),
                severity=RuleSeverity(r.severity.value),
                check_points=r.check_points,
                pass_criteria=r.pass_criteria,
                fail_examples=[],
                evidence_requirements=[],
            )
            for r in data.rules
        ],
        evidence_requirements=[],
        report_template="default",
    )


def _apply_compliance_update(existing: Compliance, data: ComplianceUpdate) -> Compliance:
    """Apply update to existing compliance."""
    rules = existing.rules
    if data.rules is not None:
        rules = [
            Rule(
                id=r.id,
                title=r.title,
                description=r.description,
                category=RuleCategory(r.category.value),
                severity=RuleSeverity(r.severity.value),
                check_points=r.check_points,
                pass_criteria=r.pass_criteria,
                fail_examples=[],
                evidence_requirements=[],
            )
            for r in data.rules
        ]

    return Compliance(
        id=existing.id,
        name=data.name or existing.name,
        version=data.version or existing.version,
        jurisdiction=existing.jurisdiction,
        scope=existing.scope,
        description=data.description if data.description is not None else existing.description,
        rules=rules,
        evidence_requirements=existing.evidence_requirements,
        report_template=existing.report_template,
    )


def _artifact_to_response(a: Artifact) -> ArtifactResponse:
    """Convert Artifact domain model to API response."""
    provenance = None
    if a.provenance:
        provenance = ProvenanceSchema(
            source=a.provenance.source,
            commit_hash=getattr(a.provenance, "commit_hash", None),
            branch=getattr(a.provenance, "branch", None),
        )

    return ArtifactResponse(
        id=a.id,
        name=a.name,
        type=ArtifactTypeEnum(a.type.value),
        locator=a.locator,
        access_method=AccessMethodEnum(a.access_method.value),
        description=a.description,
        tags=a.tags,
        provenance=provenance,
        metadata=getattr(a, "metadata", {}),
    )


def _request_to_artifact(data: ArtifactCreate) -> Artifact:
    """Convert API request to Artifact domain model."""
    provenance = None
    if data.provenance:
        provenance = Provenance(
            source=data.provenance.source,
            commit_hash=data.provenance.commit_hash,
            branch=data.provenance.branch,
        )

    return Artifact(
        id=data.id,
        name=data.name,
        type=ArtifactType(data.type.value),
        locator=data.locator,
        access_method=AccessMethod(data.access_method.value),
        description=data.description,
        tags=data.tags,
        provenance=provenance,
    )


def _apply_artifact_update(existing: Artifact, data: ArtifactUpdate) -> Artifact:
    """Apply update to existing artifact."""
    return Artifact(
        id=existing.id,
        name=data.name or existing.name,
        type=existing.type,
        locator=existing.locator,
        access_method=existing.access_method,
        description=data.description if data.description is not None else existing.description,
        tags=data.tags if data.tags is not None else existing.tags,
        provenance=existing.provenance,
    )


def _audit_to_run_response(audit: dict[str, Any]) -> AuditRunResponse:
    """Convert audit dict to AuditRunResponse."""
    return AuditRunResponse(
        id=audit.get("id", ""),
        compliance_ids=audit.get("compliance_ids", []),
        artifact_ids=audit.get("artifact_ids", []),
        status=audit.get("status", "unknown"),
        started_at=datetime.fromisoformat(audit["created_at"]) if audit.get("created_at") else datetime.now(),
        completed_at=datetime.fromisoformat(audit["completed_at"]) if audit.get("completed_at") else None,
    )


# ============ Compliance CRUD Endpoints ============


@app.get("/api/compliances/crud", response_model=list[ComplianceResponse])
async def list_compliances_crud(jurisdiction: str | None = None):
    """List all compliances with full details (CRUD version)."""
    registry = get_compliance_registry()
    items = registry.list_all()

    if jurisdiction:
        items = [c for c in items if c.jurisdiction == jurisdiction]

    return [_compliance_to_response(c) for c in items]


@app.get("/api/compliances/{compliance_id}", response_model=ComplianceResponse)
async def get_compliance_by_id(compliance_id: str):
    """Get a specific compliance by ID."""
    registry = get_compliance_registry()
    c = registry.get(compliance_id)
    if not c:
        raise HTTPException(status_code=404, detail=f"Compliance {compliance_id} not found")
    return _compliance_to_response(c)


@app.post("/api/compliances", response_model=ComplianceResponse, status_code=201)
async def create_compliance(data: ComplianceCreate):
    """Create a new compliance."""
    registry = get_compliance_registry()

    if registry.get(data.id):
        raise HTTPException(status_code=409, detail=f"Compliance {data.id} already exists")

    compliance = _request_to_compliance(data)
    registry.register(compliance)
    return _compliance_to_response(compliance)


@app.put("/api/compliances/{compliance_id}", response_model=ComplianceResponse)
async def update_compliance(compliance_id: str, data: ComplianceUpdate):
    """Update an existing compliance."""
    registry = get_compliance_registry()
    existing = registry.get(compliance_id)

    if not existing:
        raise HTTPException(status_code=404, detail=f"Compliance {compliance_id} not found")

    updated = _apply_compliance_update(existing, data)
    registry.register_or_update(updated)
    return _compliance_to_response(updated)


@app.delete("/api/compliances/{compliance_id}", status_code=204)
async def delete_compliance(compliance_id: str):
    """Delete a compliance."""
    registry = get_compliance_registry()

    if not registry.get(compliance_id):
        raise HTTPException(status_code=404, detail=f"Compliance {compliance_id} not found")

    registry.unregister(compliance_id)


@app.post("/api/compliances/load-from-supabase", response_model=ComplianceResponse)
async def load_compliance_from_supabase(
    document_id: int | None = None,
    language: str = "ko",
    compliance_id: str | None = None,
):
    """Load compliance items from Supabase database."""
    registry = get_compliance_registry()
    try:
        c = await registry.load_from_supabase(
            document_id=document_id,
            language=language,
            compliance_id=compliance_id,
        )
        return _compliance_to_response(c)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load from Supabase: {e}")


# ============ Artifact CRUD Endpoints ============


@app.get("/api/artifacts/crud", response_model=list[ArtifactResponse])
async def list_artifacts_crud(artifact_type: str | None = None, tag: str | None = None):
    """List all artifacts with full details (CRUD version)."""
    registry = get_artifact_registry()
    items = registry.list_all()

    if artifact_type:
        items = [a for a in items if a.type.value == artifact_type]
    if tag:
        items = [a for a in items if tag in a.tags]

    return [_artifact_to_response(a) for a in items]


@app.get("/api/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact_by_id(artifact_id: str):
    """Get a specific artifact by ID."""
    registry = get_artifact_registry()
    a = registry.get(artifact_id)
    if not a:
        raise HTTPException(status_code=404, detail=f"Artifact {artifact_id} not found")
    return _artifact_to_response(a)


@app.post("/api/artifacts", response_model=ArtifactResponse, status_code=201)
async def create_artifact(data: ArtifactCreate):
    """Create a new artifact."""
    registry = get_artifact_registry()

    if registry.get(data.id):
        raise HTTPException(status_code=409, detail=f"Artifact {data.id} already exists")

    artifact = _request_to_artifact(data)
    registry.register(artifact)
    return _artifact_to_response(artifact)


@app.put("/api/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def update_artifact(artifact_id: str, data: ArtifactUpdate):
    """Update an existing artifact."""
    registry = get_artifact_registry()
    existing = registry.get(artifact_id)

    if not existing:
        raise HTTPException(status_code=404, detail=f"Artifact {artifact_id} not found")

    updated = _apply_artifact_update(existing, data)
    registry.register_or_update(updated)
    return _artifact_to_response(updated)


@app.delete("/api/artifacts/{artifact_id}", status_code=204)
async def delete_artifact(artifact_id: str):
    """Delete an artifact."""
    registry = get_artifact_registry()

    if not registry.get(artifact_id):
        raise HTTPException(status_code=404, detail=f"Artifact {artifact_id} not found")

    registry.unregister(artifact_id)


@app.post("/api/artifacts/import-github", response_model=GitHubImportResponse)
async def import_artifacts_from_github(data: GitHubImportRequest):
    """Import artifacts from a GitHub repository."""
    registry = get_artifact_registry()

    try:
        artifacts = await registry.register_github_repository(
            repo_url=data.repo_url,
            branch=data.branch,
            file_patterns=data.file_patterns,
        )
        return GitHubImportResponse(
            imported_count=len(artifacts),
            artifacts=[_artifact_to_response(a) for a in artifacts],
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/artifacts/register-file", response_model=ArtifactResponse)
async def register_file_as_artifact(file_path: str, artifact_id: str | None = None):
    """Register a local file as an artifact."""
    registry = get_artifact_registry()

    try:
        artifact = registry.register_file(file_path=file_path, artifact_id=artifact_id)
        return _artifact_to_response(artifact)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ Evidence/Findings Query Endpoints ============


@app.get("/api/evidence", response_model=list[EvidenceResponse])
async def list_evidence(
    rule_id: str | None = None,
    artifact_id: str | None = None,
    audit_run_id: str | None = None,
):
    """List evidence records (placeholder - returns empty for now)."""
    # TODO: Implement when DB persistence for evidence is ready
    return []


@app.get("/api/findings", response_model=list[FindingResponse])
async def list_findings(
    rule_id: str | None = None,
    artifact_id: str | None = None,
    status: str | None = None,
):
    """List finding records (placeholder - returns empty for now)."""
    # TODO: Implement when DB persistence for findings is ready
    return []


@app.get("/api/audit-runs", response_model=list[AuditRunResponse])
async def list_audit_runs(limit: int = 50, offset: int = 0):
    """List audit run history from in-memory store."""
    runs = list(audits_store.values())[offset : offset + limit]
    return [_audit_to_run_response(r) for r in runs]


@app.get("/api/audit-runs/{run_id}", response_model=AuditRunResponse)
async def get_audit_run(run_id: str):
    """Get a specific audit run by ID."""
    if run_id not in audits_store:
        raise HTTPException(status_code=404, detail=f"Audit run {run_id} not found")
    return _audit_to_run_response(audits_store[run_id])


# ============ DB Admin Endpoints ============


@app.get("/api/db/status", response_model=DBStatusResponse)
async def get_db_status():
    """Get database connection status."""
    compliance_registry = get_compliance_registry()
    artifact_registry = get_artifact_registry()

    return DBStatusResponse(
        connected=bool(settings.supabase_url),
        provider="supabase",
        compliance_count=len(compliance_registry.list_all()),
        artifact_count=len(artifact_registry.list_all()),
    )


@app.post("/api/db/sync", response_model=DBSyncResponse)
async def sync_database(data: DBSyncRequest):
    """Sync registries with database."""
    errors: list[str] = []
    compliances_synced = 0
    artifacts_synced = 0

    if data.sync_compliances:
        try:
            registry = get_compliance_registry()
            await registry.load_from_db()
            compliances_synced = len(registry.list_all())
        except Exception as e:
            errors.append(f"Compliance sync failed: {e}")

    if data.sync_artifacts:
        try:
            registry = get_artifact_registry()
            await registry.load_from_db()
            artifacts_synced = len(registry.list_all())
        except Exception as e:
            errors.append(f"Artifact sync failed: {e}")

    return DBSyncResponse(
        success=len(errors) == 0,
        compliances_synced=compliances_synced,
        artifacts_synced=artifacts_synced,
        errors=errors,
    )


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
