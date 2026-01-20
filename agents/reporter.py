from __future__ import annotations

import logging
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from agents.config import REPORT_OUTPUT_DIR, REPORT_POLL_INTERVAL
from agents.database import DatabaseClient
from agents.logging_utils import configure_logging
from agents.prompt_loader import load_prompt

logger = logging.getLogger("agents.reporter")
REPORTER_PROMPT = load_prompt("reporter")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _summarize_status(results: List[Dict]) -> Dict[str, int]:
    counter = Counter(result.get("status", "UNKNOWN") for result in results)
    return dict(counter)


def _format_evidence(evidence: str | None, indent: str = "") -> str:
    if not evidence:
        return f"{indent}- 증거: (없음)"
    lines = [line for line in evidence.splitlines() if line.strip()]
    if len(lines) == 1:
        return f"{indent}- 증거: {lines[0]}"
    joined = "\n".join(lines)
    return f"{indent}- 증거:\n\n```text\n{joined}\n```\n"


def _extract_recommendation(reasoning: str, status: str) -> str:
    if not reasoning:
        return "수정 방안 없음."
    for line in reasoning.splitlines():
        stripped = line.strip()
        if stripped.startswith("수정 방안:"):
            return stripped.replace("수정 방안:", "", 1).strip() or "수정 방안 없음."
    if status == "FAIL":
        return "요구사항을 충족하도록 구현을 보완한 뒤 재검증하세요."
    if status == "ERROR":
        return "오류 원인을 해결한 뒤 재검증하세요."
    return "조치 필요 없음."


def _render_result_row(result: Dict, compliance_item: Dict | None) -> str:
    status = result.get("status") or "UNKNOWN"
    reasoning = result.get("reasoning") or "사유가 제공되지 않았습니다."
    evidence_text = result.get("evidence")
    item_text = (compliance_item or {}).get("item_text") or "(요구사항 텍스트 없음)"
    section = (compliance_item or {}).get("section")
    page = (compliance_item or {}).get("page")

    item_meta = []
    if section:
        item_meta.append(f"섹션: {section}")
    if page:
        item_meta.append(f"페이지: {page}")
    item_meta_text = ", ".join(item_meta) if item_meta else "섹션/페이지: (제공되지 않음)"

    if status == "PASS":
        explanation = "아래 근거와 증거를 기준으로 요구사항을 충족한다고 판단했습니다."
        recommendation = "조치 필요 없음."
    elif status == "FAIL":
        explanation = "요구사항을 충족하지 못했습니다. 근거와 증거를 확인하세요."
        recommendation = _extract_recommendation(reasoning, status)
    else:
        explanation = "이 항목은 정상적으로 평가되지 않았습니다. 사유와 증거를 확인하세요."
        recommendation = _extract_recommendation(reasoning, status)

    evidence_block = _format_evidence(evidence_text)

    return (
        f"### 컴플라이언스 항목 {result.get('compliance_item_id')}\n"
        f"- 상태: {status}\n"
        f"- 요구사항: {item_text}\n"
        f"- {item_meta_text}\n"
        f"- 설명: {explanation}\n"
        f"- 근거: {reasoning}\n"
        f"{evidence_block}\n"
        f"- 수정 방안: {recommendation}\n"
    )


def _write_report(scan_id: str, content: str) -> Path:
    REPORT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_OUTPUT_DIR / f"scan-{scan_id}.md"
    report_path.write_text(content, encoding="utf-8")
    return report_path


def generate_report(
    scan: Dict,
    results: List[Dict],
    compliance_items: Dict[int, Dict],
) -> Tuple[str, Path]:
    summary = _summarize_status(results)
    total_results = sum(summary.values())
    failures = summary.get("FAIL", 0) + summary.get("ERROR", 0)
    lines = [
        "# Kompline 컴플라이언스 보고서",
        "",
        "## 스캔 메타데이터",
        "",
        f"- 스캔 ID: {scan.get('id')}",
        f"- 저장소 URL: {scan.get('repo_url')}",
        f"- 생성 시각(UTC): {_utc_now()}",
        "",
        "## 요약",
        "",
    ]
    for status, count in sorted(summary.items()):
        lines.append(f"- {status}: {count}")

    lines.extend(
        [
            "",
            f"- 총 점검 수: {total_results}",
            f"- 조치 필요 건수: {failures}",
            "",
            "## 결과 상세",
            "",
        ]
    )
    for result in results:
        compliance_item = compliance_items.get(result.get("compliance_item_id"))
        lines.append(_render_result_row(result, compliance_item))

    content = "\n".join(lines).strip() + "\n"
    report_path = _write_report(scan["id"], content)
    return content, report_path


def run_once(db: DatabaseClient) -> int:
    active = db.list_active_scans(["PROCESSING", "REPORT_GENERATING"])
    if not active:
        return 0

    processed = 0
    for scan in active:
        scan_id = scan["id"]
        pending = db.count_pending_results(scan_id)
        if pending > 0:
            continue

        db.update_scan_status(scan_id, "REPORT_GENERATING")
        results = db.list_scan_results(scan_id)
        compliance_items: Dict[int, Dict] = {}
        for result in results:
            item_id = result.get("compliance_item_id")
            if item_id is None or item_id in compliance_items:
                continue
            compliance_items[item_id] = db.get_compliance_item(item_id) or {}
        content, report_path = generate_report(scan, results, compliance_items)
        try:
            db.update_scan_status(
                scan_id,
                "COMPLETED",
                report_url=str(report_path),
                report_markdown=content,
            )
        except Exception:
            logger.exception("Failed to store report_markdown for scan=%s", scan_id)
            db.update_scan_status(scan_id, "COMPLETED", report_url=str(report_path))
        logger.info("Report generated for scan=%s path=%s", scan_id, report_path)
        processed += 1

    return processed


def run_loop() -> None:
    configure_logging()
    db = DatabaseClient.from_env()
    logger.info("Reporter started")
    while True:
        try:
            count = run_once(db)
            if count == 0:
                time.sleep(REPORT_POLL_INTERVAL)
        except Exception:
            logger.exception("Reporter error")
            time.sleep(REPORT_POLL_INTERVAL)


if __name__ == "__main__":
    run_loop()
