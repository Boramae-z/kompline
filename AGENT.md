# AGENT.md

## Purpose
This file provides project-specific instructions for Codex, Claude.

## Instructions
- Follow all instructions in this file when working in this repository.
- Keep edits minimal and focused on the user’s request.
- Prefer `rg` for search and `apply_patch` for small, single-file edits.
- Do not run network commands without explicit approval.
- Do not modify files outside the workspace.

## Commit Message Convention

### Reasoning Log Format

Commit messages are a Reasoning Log that preserves decision context and history.
Why comes first, What comes after — state intent before implementation details.

```
{Verb} {Title}

Why: {One or two lines stating intent/purpose}

What:
- {Summary of 1–2 key changes}
```

### Example

```
Add Admin Dashboard for platform management

Why: Platform admins need to monitor and manage users, projects, and global settings from a central location

What:
- /admin page with Dashboard-first UX (stats cards + management tabs)
- API routes proxying to backend /admin/* endpoints
```

### Rules

1. Why first: state intent before implementation details (What).
2. English only: code, comments, and commit messages are all in English.
3. Human approval required: every commit must be created only after explicit human approval.
4. No AI attribution: no "Generated with", "Co-Authored-By", or similar AI markers.
5. Semantic units: commit in meaningful, logically complete units of work.

### Verb examples

Add, Fix, Refactor, Update, Remove, Use, Improve, Simplify

## Branch Rules

- Branch naming: `{type}/{short-description}` in lowercase with hyphens.
- Allowed types: `feature`, `fix`, `chore`, `refactor`, `docs`, `test`.
- Keep names concise; include a ticket/issue ID if one exists (e.g., `feature/1234-add-login`).

## Project Context

When working on this project, always read the following documents first:

- **[docs/IMPLEMENTATION_PLAN.md](./docs/IMPLEMENTATION_PLAN.md)**: Architecture, core abstractions, implementation phases, and file structure for the Kompline multi-agent compliance system.

## Notes
- Add additional project rules here as needed.
