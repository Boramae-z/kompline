"""Pydantic schemas for API request/response models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# === Enums ===
class ArtifactTypeEnum(str, Enum):
    CODE = "code"
    DOCUMENT = "document"
    CONFIG = "config"
    DATA = "data"


class AccessMethodEnum(str, Enum):
    FILE_READ = "file_read"
    API_CALL = "api_call"
    GITHUB = "github"


class RuleCategoryEnum(str, Enum):
    ALGORITHM_FAIRNESS = "algorithm_fairness"
    TRANSPARENCY = "transparency"
    DATA_HANDLING = "data_handling"
    DISCLOSURE = "disclosure"
    PRIVACY = "privacy"
    SECURITY = "security"


class RuleSeverityEnum(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ComplianceStatusEnum(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


# === Compliance Schemas ===
class RuleSchema(BaseModel):
    """Schema for compliance rule."""

    id: str
    title: str
    description: str
    category: RuleCategoryEnum
    severity: RuleSeverityEnum
    check_points: list[str] = Field(default_factory=list)
    pass_criteria: str = ""


class ComplianceCreate(BaseModel):
    """Schema for creating a new compliance."""

    id: str
    name: str
    version: str = "1.0"
    jurisdiction: str = "KR"
    scope: list[str] = Field(default_factory=list)
    description: str = ""
    rules: list[RuleSchema] = Field(default_factory=list)


class ComplianceUpdate(BaseModel):
    """Schema for updating an existing compliance."""

    name: str | None = None
    version: str | None = None
    description: str | None = None
    rules: list[RuleSchema] | None = None


class ComplianceResponse(BaseModel):
    """Schema for compliance response."""

    id: str
    name: str
    version: str
    jurisdiction: str
    scope: list[str]
    description: str
    rules: list[RuleSchema]
    metadata: dict[str, Any] = Field(default_factory=dict)


# === Artifact Schemas ===
class ProvenanceSchema(BaseModel):
    """Schema for artifact provenance."""

    source: str
    commit_hash: str | None = None
    branch: str | None = None


class ArtifactCreate(BaseModel):
    """Schema for creating a new artifact."""

    id: str
    name: str
    type: ArtifactTypeEnum
    locator: str
    access_method: AccessMethodEnum
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    provenance: ProvenanceSchema | None = None


class ArtifactUpdate(BaseModel):
    """Schema for updating an existing artifact."""

    name: str | None = None
    description: str | None = None
    tags: list[str] | None = None


class ArtifactResponse(BaseModel):
    """Schema for artifact response."""

    id: str
    name: str
    type: ArtifactTypeEnum
    locator: str
    access_method: AccessMethodEnum
    description: str
    tags: list[str]
    provenance: ProvenanceSchema | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GitHubImportRequest(BaseModel):
    """Schema for GitHub import request."""

    repo_url: str
    branch: str = "main"
    file_patterns: list[str] = Field(default_factory=lambda: ["**/*.py"])


class GitHubImportResponse(BaseModel):
    """Schema for GitHub import response."""

    imported_count: int
    artifacts: list[ArtifactResponse]


# === Query Schemas ===
class EvidenceResponse(BaseModel):
    """Schema for evidence response."""

    id: str
    rule_id: str
    artifact_id: str
    content: str
    extracted_at: datetime


class FindingResponse(BaseModel):
    """Schema for finding response."""

    id: str
    rule_id: str
    artifact_id: str
    status: ComplianceStatusEnum
    message: str
    created_at: datetime


class AuditRunResponse(BaseModel):
    """Schema for audit run response."""

    id: str
    compliance_ids: list[str]
    artifact_ids: list[str]
    status: str
    started_at: datetime
    completed_at: datetime | None = None


# === DB Admin Schemas ===
class DBStatusResponse(BaseModel):
    """Schema for database status response."""

    connected: bool
    provider: str
    compliance_count: int
    artifact_count: int


class DBSyncRequest(BaseModel):
    """Schema for database sync request."""

    sync_compliances: bool = True
    sync_artifacts: bool = True


class DBSyncResponse(BaseModel):
    """Schema for database sync response."""

    success: bool
    compliances_synced: int
    artifacts_synced: int
    errors: list[str] = Field(default_factory=list)
