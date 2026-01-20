# Kompline

Multi-agent continuous compliance system for Korean financial regulations.

## Overview

Kompline (K-compliance + Pipeline) automates algorithm fairness verification for financial platforms, targeting the **알고리즘 공정성 자가평가** (Algorithm Fairness Self-Assessment, Form 별지5) requirements mandated by Korean financial regulators.

### Key Value Proposition

| Before (Manual) | After (Kompline) |
|-----------------|------------------|
| 2-3 weeks per audit | **2-3 minutes** automated analysis |
| Single compliance at a time | **Multi-compliance parallel** verification |
| Inconsistent evidence collection | **Structured evidence** with provenance |
| Paper-based reports | **Digital 자가평가서** with audit trail |

**ROI for B2B Adoption:**
- **80% reduction** in compliance audit time
- **Consistent** rule application across all code reviews
- **Audit trail** for regulatory inspection readiness
- **Scalable** to multiple products/repositories simultaneously

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Audit Orchestrator (총괄)                         │
│  1. Build audit relations from user request                         │
│  2. Spawn Audit Agents per relation (parallel)                      │
│  3. Aggregate findings with retry on failure                        │
│  4. Generate unified compliance report                              │
└─────────────────────────────────────────────────────────────────────┘
                              │ spawn per (Compliance, Artifact)
        ┌─────────────────────┼─────────────────────────────┐
        ▼                     ▼                             ▼
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│    Audit Agent    │  │    Audit Agent    │  │    Audit Agent    │
│ (공정성, code.py) │  │ (PIPA, code.py)   │  │ (공정성, config)  │
├───────────────────┤  ├───────────────────┤  ├───────────────────┤
│ 1. Plan evidence  │  │ 1. Plan evidence  │  │ 1. Plan evidence  │
│ 2. Call Readers   │  │ 2. Call Readers   │  │ 2. Call Readers   │
│ 3. Evaluate rules │  │ 3. Evaluate rules │  │ 3. Evaluate rules │
│ 4. Emit findings  │  │ 4. Emit findings  │  │ 4. Emit findings  │
└────────┬──────────┘  └────────┬──────────┘  └────────┬──────────┘
         │ handoff to readers   │                      │
    ┌────┴────┐            ┌────┴────┐            ┌────┴────┐
    ▼         ▼            ▼         ▼            ▼         ▼
┌────────┐ ┌────────┐  ┌────────┐ ┌────────┐  ┌────────┐ ┌────────┐
│ Code   │ │  PDF   │  │ Code   │ │  PDF   │  │ Config │ │  PDF   │
│ Reader │ │ Reader │  │ Reader │ │ Reader │  │ Reader │ │ Reader │
└────────┘ └────────┘  └────────┘ └────────┘  └────────┘ └────────┘
```

### Core Concept: Audit Relation

```
Audit Relation = (Compliance, Artifact)

Examples:
- (알고리즘 공정성 자가평가, deposit_ranking.py) → Audit Agent #1
- (개인정보보호법, deposit_ranking.py)            → Audit Agent #2
- (알고리즘 공정성 자가평가, config.yaml)         → Audit Agent #3
```

One Artifact can be audited against multiple Compliances, or one Compliance can be applied to multiple Artifacts - all in parallel.

## Features

- **Multi-Agent Parallel Execution**: Spawn independent audit agents per (Compliance, Artifact) relation
- **Evidence-Based Audit**: Structured evidence collection with provenance tracking
- **LLM-Assisted Rule Evaluation**: Use OpenAI to assess rules from extracted evidence (fallback to heuristics)
- **Human-in-the-Loop**: Automatic triggers for low confidence and FAIL findings
- **자가평가서 Report Generation**: Regulatory-compliant report format with evidence references
- **Observability**: Full tracing and audit logging for inspection readiness

## Quick Start

### Prerequisites

```bash
# Python 3.11+
python --version

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows
```

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/kompline.git
cd kompline

# Install with all dependencies
pip install -e ".[dev]"
```

### Configuration

Create a `.env` file in the project root:

```env
# Required
OPENAI_API_KEY=sk-your-api-key-here

# Optional
OPENAI_MODEL=gpt-4o              # Default model
RAG_API_URL=http://localhost:8000  # RAG backend URL
LOG_LEVEL=INFO
```

### Running the Demo

#### Option 1: Quick CLI (Recommended)

```bash
kompline samples/deposit_ranking.py
```

#### Option 2: Multi-Compliance Demo Script

```bash
python -m samples.demo_scenario
```

This script registers demo compliances (알고리즘 공정성 자가평가 + 개인정보보호법), registers the sample
artifact, runs parallel audits, and prints a 자가평가서 report.

#### Option 3: FastAPI Server

```bash
# Start the API server
uvicorn api.main:app --host 0.0.0.0 --port 8888 --reload

# In another terminal, test the API
curl -X POST http://localhost:8888/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "source_code": "def rank(products): return sorted(products, key=lambda x: x.rate)",
    "compliance_ids": ["byeolji5-fairness"]
  }'
```

API Endpoints:
- `GET /` - Health check
- `POST /analyze` - Analyze source code for compliance
- `GET /reviews` - Get pending human reviews
- `GET /trace` - Get agent execution trace
- `DELETE /trace` - Clear execution trace

API Documentation: http://localhost:8080/docs (Swagger UI)

#### Option 4: Streamlit UI

```bash
# Start the Streamlit demo
streamlit run ui/app.py --server.headless true

# Open browser at http://localhost:8501
```

The UI provides:
- Code input and file upload
- Real-time agent activity log
- Interactive compliance results
- 자가평가서 report preview
- Pending review list (HITL)

## Project Structure

```
kompline/
├── kompline/
│   ├── demo_data.py               # Demo compliance/artifact bootstrap
│   ├── models/                    # Domain models
│   │   ├── compliance.py          # Compliance, Rule, EvidenceRequirement
│   │   ├── artifact.py            # Artifact, ArtifactType, Provenance
│   │   ├── audit_relation.py      # AuditRelation, RunConfig
│   │   ├── evidence.py            # Evidence, EvidenceCollection
│   │   └── finding.py             # Finding, FindingStatus
│   ├── registry/                  # Registries
│   │   ├── compliance_registry.py # ComplianceRegistry
│   │   └── artifact_registry.py   # ArtifactRegistry
│   ├── agents/
│   │   ├── audit_orchestrator.py  # Main orchestrator with retry logic
│   │   ├── audit_agent.py         # Per-relation audit agent
│   │   ├── rule_evaluator.py      # Rule evaluation with RAG
│   │   ├── report_generator.py    # Report templates
│   │   └── readers/               # Evidence readers
│   │       ├── base_reader.py     # Abstract base
│   │       ├── code_reader.py     # Python/JS code analysis
│   │       ├── pdf_reader.py      # PDF document extraction
│   │       └── config_reader.py   # YAML/JSON config parsing
│   ├── tools/
│   │   ├── code_parser.py         # AST utilities
│   │   ├── rag_query.py           # RAG with citations
│   │   └── report_export.py       # Export utilities
│   ├── guardrails/
│   │   ├── input_validator.py     # Source code validation
│   │   ├── output_validator.py    # Quality checks
│   │   ├── evidence_validator.py  # Evidence validation
│   │   └── finding_validator.py   # Finding consistency
│   ├── hitl/
│   │   ├── triggers.py            # Review trigger conditions
│   │   └── review_handler.py      # Review queue management
│   └── tracing/
│       └── logger.py              # Audit logging
│   └── utils/
│       └── json_utils.py          # LLM JSON parsing helpers
├── api/
│   └── main.py                    # FastAPI server
├── ui/
│   └── app.py                     # Streamlit demo
├── samples/
│   ├── demo_scenario.py           # Multi-compliance demo script
│   ├── compliances/               # YAML compliance definitions
│   │   ├── byeolji5_fairness.yaml
│   │   └── pipa_kr.yaml
│   └── deposit_ranking.py         # Sample code with compliance issues
├── tests/
└── docs/
    └── audits/                    # Regulatory forms (PDF)
```

## Agents Overview

| Agent | Role | Tools |
|-------|------|-------|
| **AuditOrchestrator** | Build relations, spawn agents in parallel, aggregate findings | `create_audit_relations`, `aggregate_findings` |
| **AuditAgent** | Evaluate single (Compliance, Artifact) relation | `collect_evidence`, `evaluate_rule` |
| **CodeReader** | Extract code evidence via AST parsing | `parse_code`, `detect_patterns` |
| **PDFReader** | Extract text/tables from PDF documents | `extract_text`, `extract_tables` |
| **ConfigReader** | Parse YAML/JSON configuration files | `read_config`, `validate_schema` |
| **RuleEvaluator** | (Optional) RAG-based rule matching | `query_rules`, `evaluate_compliance` |
| **ReportGenerator** | Generate regulatory format reports | `format_report`, `export_pdf` |

## Human-in-the-Loop Triggers

| Trigger | Condition | Action |
|---------|-----------|--------|
| **Low Confidence** | confidence < 70% | Queue for human review |
| **FAIL Finding** | status == FAIL | Require auditor confirmation |
| **New Pattern** | Pattern not in rule database | Flag for rule update |
| **Conflicting Evidence** | Evidence contradicts finding | Escalate to senior auditor |

## Error Handling & Retry (Planned)

Advanced retry strategies (exponential backoff, reader fallback) are planned but
not enabled in the default demo yet.

## RAG Citations (Planned)

RAG-backed citations are planned for the rule-matching pipeline. The current
demo focuses on evidence extraction and LLM/heuristic evaluation.

## Development

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=kompline --cov-report=html

# Format code
ruff format .

# Lint
ruff check .

# Type check
mypy kompline
```

## Compliance Definitions

Add new compliances via YAML:

```yaml
# samples/compliances/your_compliance.yaml
id: custom-compliance-2024
name: Custom Compliance Rules
version: "2024.01"
jurisdiction: KR
scope:
  - algorithm
  - data_handling
rules:
  - id: CUSTOM-001
    title: Rule Title
    description: What this rule checks
    category: algorithm_fairness
    severity: high
    check_points:
      - Specific check 1
      - Specific check 2
    pass_criteria: When this rule passes
    fail_examples:
      - Example of violation
```

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

For questions or support, open an issue on GitHub.
