# Kompline Agents - Implementation Plan

This document outlines the architecture and implementation plan for the **Kompline Multi-Agent System**.

## Architectural Overview

The system follows a **Dispatcher-Worker-Reporter** pattern, using Supabase as the shared state store (Message Broker).

### 1. Database Schema Extensions (Supabase)
To support the agents, we need the following tables (Schema to be applied):

*   **`scans`**: Represents a user request to audit a specific repository against specific regulations.
    *   `id` (UUID, PK)
    *   `created_at` (Timestamp)
    *   `repo_url` (Text)
    *   `status` (Text: `QUEUED`, `PROCESSING`, `REPORT_GENERATING`, `COMPLETED`, `FAILED`)
    *   `report_url` (Text, optional)

*   **`scan_junction`**: Links scans to documents (regulations).
    *   `scan_id` (UUID, FK)
    *   `document_id` (UUID, FK)

*   **`scan_results`**: Individual validation tasks for each compliance item.
    *   `id` (UUID, PK)
    *   `scan_id` (UUID, FK)
    *   `compliance_item_id` (Int, FK)
    *   `status` (Text: `PENDING`, `PASS`, `FAIL`, `ERROR`)
    *   `reasoning` (Text)
    *   `evidence` (Text) - Snippets or file paths
    *   `updated_at` (Timestamp)

### 2. Components

#### A. Orchestrator (Dispatcher)
*   **Role**: Monitors new `scans` in `QUEUED` state.
*   **Action**:
    1.  Fetches the scan details and associated documents.
    2.  Queries `compliance_items` for those documents.
    3.  Inserts a row into `scan_results` for EACH compliance item with status `PENDING`.
    4.  Updates `scan` status to `PROCESSING`.

#### B. Validator Agents (Workers)
*   **Role**: Validates individual compliance items against the codebase.
*   **Scalability**: Can run multiple instances in parallel.
*   **Action**:
    1.  Polls `scan_results` for `PENDING` items (with row locking if possible, or simple claim mechanism).
    2.  **Context Loading**: Fetches the code (git clone or RAG retrieval from vector store).
    3.  **LLM Check**: Uses prompts to check if `repo` satisfies `compliance_item`.
    4.  **Update**: Writes result (`PASS`/`FAIL`, `reasoning`) to `scan_results`.

#### C. Reporter Agent
*   **Role**: Generates the final output.
*   **Action**:
    1.  Monitors `scans` where all associated `scan_results` are NOT `PENDING`.
    2.  Aggregates all results.
    3.  Generates a Markdown/PDF report.
    4.  Uploads report to Supabase Storage (optional) or saves text.
    5.  Updates `scan` status to `COMPLETED`.

## Implementation Roadmap

### Phase 1: Environment & Setup
- [ ] Setup Python environment (virtualenv/poetry).
- [ ] Install dependencies (`supabase`, `langchain`, `openai`, `pydantic`).

### Phase 2: Core Logic
- [ ] Implement `DatabaseClient` (Supabase wrapper).
- [ ] Implement `GitLoader` (Clones repo, maybe indexes it).
- [ ] Implement `Orchestrator` script.
- [ ] Implement `Validator` agent loop.

### Phase 3: Integration
- [ ] Run `Orchestrator` and `Validator` together.
- [ ] Verify end-to-end flow with a test scan.
