"""Evidence validation guardrails."""

from dataclasses import dataclass
from typing import Any

from kompline.models import Evidence, EvidenceCollection, EvidenceType


@dataclass
class ValidationResult:
    """Result of validation."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]

    @classmethod
    def valid(cls, warnings: list[str] | None = None) -> "ValidationResult":
        """Create a valid result."""
        return cls(is_valid=True, errors=[], warnings=warnings or [])

    @classmethod
    def invalid(cls, errors: list[str], warnings: list[str] | None = None) -> "ValidationResult":
        """Create an invalid result."""
        return cls(is_valid=False, errors=errors, warnings=warnings or [])


class EvidenceValidator:
    """Validates evidence for quality and completeness."""

    def __init__(
        self,
        min_content_length: int = 10,
        max_content_length: int = 50000,
        require_provenance: bool = True,
    ):
        """Initialize the validator.

        Args:
            min_content_length: Minimum evidence content length.
            max_content_length: Maximum evidence content length.
            require_provenance: Whether provenance is required.
        """
        self.min_content_length = min_content_length
        self.max_content_length = max_content_length
        self.require_provenance = require_provenance

    def validate(self, evidence: Evidence) -> ValidationResult:
        """Validate a single evidence item.

        Args:
            evidence: The evidence to validate.

        Returns:
            ValidationResult with any errors or warnings.
        """
        errors = []
        warnings = []

        # Check required fields
        if not evidence.id:
            errors.append("Evidence ID is required")

        if not evidence.relation_id:
            errors.append("Relation ID is required")

        if not evidence.source:
            errors.append("Source is required")

        # Check content
        if not evidence.content:
            errors.append("Evidence content is empty")
        elif len(evidence.content) < self.min_content_length:
            warnings.append(f"Evidence content is very short ({len(evidence.content)} chars)")
        elif len(evidence.content) > self.max_content_length:
            errors.append(f"Evidence content exceeds maximum length ({len(evidence.content)} > {self.max_content_length})")

        # Check provenance
        if self.require_provenance and not evidence.provenance:
            warnings.append("Evidence lacks provenance information")

        # Type-specific validation
        type_result = self._validate_by_type(evidence)
        errors.extend(type_result.errors)
        warnings.extend(type_result.warnings)

        if errors:
            return ValidationResult.invalid(errors, warnings)
        return ValidationResult.valid(warnings)

    def _validate_by_type(self, evidence: Evidence) -> ValidationResult:
        """Validate evidence based on its type.

        Args:
            evidence: The evidence to validate.

        Returns:
            ValidationResult for type-specific checks.
        """
        warnings = []

        if evidence.type == EvidenceType.CODE_SNIPPET:
            # Code should have line number
            if evidence.line_number is None:
                warnings.append("Code evidence should include line number")

        elif evidence.type == EvidenceType.DOCUMENT_EXCERPT:
            # Document should have page number
            if evidence.page_number is None:
                warnings.append("Document evidence should include page number")

        elif evidence.type == EvidenceType.CONFIG_VALUE:
            # Config should have key path in metadata
            if not evidence.metadata.get("key_path"):
                warnings.append("Config evidence should include key path")

        return ValidationResult.valid(warnings)

    def validate_collection(self, collection: EvidenceCollection) -> ValidationResult:
        """Validate an evidence collection.

        Args:
            collection: The collection to validate.

        Returns:
            Aggregated validation result.
        """
        all_errors = []
        all_warnings = []

        if len(collection) == 0:
            all_warnings.append("Evidence collection is empty")

        for evidence in collection:
            result = self.validate(evidence)
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)

        # Check for duplicate IDs
        ids = [e.id for e in collection]
        if len(ids) != len(set(ids)):
            all_errors.append("Duplicate evidence IDs found")

        if all_errors:
            return ValidationResult.invalid(all_errors, all_warnings)
        return ValidationResult.valid(all_warnings)


def validate_evidence(evidence: Evidence) -> ValidationResult:
    """Validate evidence using default settings.

    Args:
        evidence: The evidence to validate.

    Returns:
        ValidationResult.
    """
    validator = EvidenceValidator()
    return validator.validate(evidence)


def validate_evidence_collection(collection: EvidenceCollection) -> ValidationResult:
    """Validate an evidence collection using default settings.

    Args:
        collection: The collection to validate.

    Returns:
        ValidationResult.
    """
    validator = EvidenceValidator()
    return validator.validate_collection(collection)
