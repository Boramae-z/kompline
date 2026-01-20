"""Streamlit demo UI for Kompline."""

import streamlit as st
import asyncio
import httpx
from datetime import datetime
from pathlib import Path

# Page config
st.set_page_config(
    page_title="Kompline - Algorithm Fairness Verification",
    page_icon="⚖️",
    layout="wide",
)

# Configuration
API_URL = "http://localhost:8080"

# Initialize session state
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "trace_events" not in st.session_state:
    st.session_state.trace_events = []
if "pending_reviews" not in st.session_state:
    st.session_state.pending_reviews = []
if "error_message" not in st.session_state:
    st.session_state.error_message = None
if "use_api" not in st.session_state:
    st.session_state.use_api = True


# Sample code for demo
SAMPLE_CODE_COMPLIANT = '''"""Compliant deposit ranking algorithm."""

RANKING_WEIGHTS = {
    "interest_rate": 0.5,
    "accessibility": 0.2,
    "term_flexibility": 0.15,
    "stability": 0.15,
}

def rank_deposits(products, stability_ratings=None):
    """Rank deposits by documented, fair criteria."""
    scored = []
    for product in products:
        score = (
            RANKING_WEIGHTS["interest_rate"] * product.interest_rate / 10
            + RANKING_WEIGHTS["accessibility"] * 0.5
            + RANKING_WEIGHTS["term_flexibility"] * 0.5
            + RANKING_WEIGHTS["stability"] * stability_ratings.get(product.bank, 0.5)
        )
        scored.append((product, score))
    return sorted(scored, key=lambda x: x[1], reverse=True)
'''

SAMPLE_CODE_ISSUES = '''"""Ranking with compliance issues."""
import random

def rank_deposits_biased(products, preferred_banks=None):
    """WARNING: Contains undocumented preferences."""
    scored = []
    for product in products:
        score = product.interest_rate / 10

        # ISSUE: Undocumented affiliate boost
        if product.is_affiliated:
            score *= 1.2

        # ISSUE: Hidden preference
        if product.bank in (preferred_banks or []):
            score *= 1.1

        scored.append((product, score))

    # ISSUE: Undisclosed randomization
    random.shuffle(scored)
    return sorted(scored, key=lambda x: x[1], reverse=True)
'''


async def analyze_via_api(source_code: str, require_review: bool = True) -> dict:
    """Call the FastAPI backend for analysis."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{API_URL}/analyze",
            json={
                "source_code": source_code,
                "require_review": require_review,
            },
        )
        response.raise_for_status()
        return response.json()


async def analyze_local(source_code: str, require_review: bool = True) -> dict:
    """Run analysis locally without API."""
    try:
        from kompline.runner import KomplineRunner
        runner = KomplineRunner()
        result = await runner.analyze(source_code, require_review=require_review)
        return {
            "success": result.get("success", False),
            "report": result.get("report"),
            "pending_reviews": [],
            "trace": runner.get_trace(),
            "error": result.get("error"),
        }
    except Exception as e:
        return {
            "success": False,
            "report": None,
            "pending_reviews": [],
            "trace": [],
            "error": str(e),
        }


async def get_pending_reviews() -> list:
    """Get pending reviews from API."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{API_URL}/reviews")
            response.raise_for_status()
            return response.json().get("pending", [])
    except Exception:
        return []


async def submit_review(request_id: str, action: str, comment: str = "") -> dict:
    """Submit a review response."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{API_URL}/reviews/{request_id}",
            json={
                "request_id": request_id,
                "action": action,
                "comment": comment,
            },
        )
        response.raise_for_status()
        return response.json()


def run_analysis(source_code: str, require_review: bool, use_api: bool):
    """Run the analysis synchronously."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        if use_api:
            return loop.run_until_complete(analyze_via_api(source_code, require_review))
        else:
            return loop.run_until_complete(analyze_local(source_code, require_review))
    finally:
        loop.close()


def main():
    st.title("⚖️ Kompline")
    st.subheader("Algorithm Fairness Continuous Verification System")
    st.caption("Korean Financial Regulation Compliance - Appendix 5 Self-Assessment")

    st.divider()

    # Sidebar
    with st.sidebar:
        st.header("Settings")

        # API connection toggle
        use_api = st.checkbox(
            "Use API Server",
            value=st.session_state.use_api,
            help=f"Connect to FastAPI server at {API_URL}. Uncheck to run locally.",
        )
        st.session_state.use_api = use_api

        if use_api:
            # Check API health
            try:
                import httpx
                with httpx.Client(timeout=2.0) as client:
                    resp = client.get(f"{API_URL}/")
                    if resp.status_code == 200:
                        st.success("API Connected")
                    else:
                        st.warning("API returned error")
            except Exception:
                st.error("API not available")
                st.caption(f"Start server: `uvicorn api.main:app --port 8080`")

        require_review = st.checkbox("Enable Human-in-the-Loop", value=True)
        show_trace = st.checkbox("Show Real-time Logs", value=True)

        st.divider()

        st.header("Sample Code")
        if st.button("Load Compliant Code", use_container_width=True):
            st.session_state.code_input = SAMPLE_CODE_COMPLIANT
            st.session_state.analysis_result = None
            st.session_state.error_message = None
        if st.button("Load Non-compliant Code", use_container_width=True):
            st.session_state.code_input = SAMPLE_CODE_ISSUES
            st.session_state.analysis_result = None
            st.session_state.error_message = None

    # Main content
    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("Source Code Input")

        code_input = st.text_area(
            "Enter Python code to analyze",
            value=st.session_state.get("code_input", SAMPLE_CODE_COMPLIANT),
            height=400,
            key="code_area",
        )

        analyze_button = st.button("Start Analysis", type="primary", use_container_width=True)

        if analyze_button:
            st.session_state.error_message = None
            st.session_state.analysis_result = None

            with st.spinner("Analyzing..."):
                try:
                    result = run_analysis(
                        code_input,
                        require_review,
                        st.session_state.use_api,
                    )

                    if result.get("success") and result.get("report"):
                        st.session_state.analysis_result = result["report"]
                        st.session_state.trace_events = result.get("trace", [])
                        st.session_state.pending_reviews = result.get("pending_reviews", [])
                    elif result.get("error"):
                        st.session_state.error_message = result["error"]
                    else:
                        st.session_state.error_message = "Analysis returned no results"

                except httpx.ConnectError:
                    st.session_state.error_message = (
                        f"Cannot connect to API at {API_URL}. "
                        "Start the server or disable 'Use API Server'."
                    )
                except httpx.HTTPStatusError as e:
                    st.session_state.error_message = f"API error: {e.response.text}"
                except Exception as e:
                    st.session_state.error_message = f"Analysis failed: {str(e)}"

    with col2:
        st.header("Analysis Results")

        # Show error if present
        if st.session_state.error_message:
            st.error(st.session_state.error_message)

        if st.session_state.analysis_result:
            result = st.session_state.analysis_result
            status = result.get("overall_status", "UNKNOWN")

            # Status badge
            if status == "COMPLIANT":
                st.success("COMPLIANT - Regulation Satisfied")
            elif status == "NON_COMPLIANT":
                st.error("NON_COMPLIANT - Violations Found")
            elif status == "PENDING_REVIEW":
                st.warning("PENDING_REVIEW - Human Review Required")
            else:
                st.info(f"Status: {status}")

            # Summary metrics
            summary = result.get("summary", {"PASS": 0, "FAIL": 0, "REVIEW": 0})
            cols = st.columns(3)
            cols[0].metric("PASS", summary.get("PASS", 0))
            cols[1].metric(
                "FAIL",
                summary.get("FAIL", 0),
                delta=None if summary.get("FAIL", 0) == 0 else f"-{summary.get('FAIL', 0)}",
            )
            cols[2].metric("REVIEW", summary.get("REVIEW", 0))

            st.divider()

            # Detailed checks
            st.subheader("Detailed Check Results")
            for check in result.get("checks", []):
                status_icon = {"PASS": "✅", "FAIL": "❌", "REVIEW": "⚠️"}.get(
                    check.get("status", ""), "❓"
                )
                rule_id = check.get("rule_id", "Unknown")
                rule_title = check.get("rule_title", "")

                with st.expander(f"{status_icon} {rule_id} - {rule_title}"):
                    st.write(f"**Status**: {check.get('status', 'Unknown')}")
                    st.write(f"**Confidence**: {check.get('confidence', 0):.0%}")

                    # Evidence with citations
                    st.write("**Evidence**:")
                    for evidence in check.get("evidence", []):
                        st.write(f"- {evidence}")

                    # Citations (from RAG)
                    citations = check.get("citations", [])
                    if citations:
                        st.write("**Source Citations**:")
                        for citation in citations:
                            source = citation.get("source", "Unknown")
                            text = citation.get("text", "")
                            relevance = citation.get("relevance", 0)
                            st.caption(f"📚 [{source}] {text} (relevance: {relevance:.0%})")

                    if check.get("recommendation"):
                        st.warning(f"**Recommendation**: {check['recommendation']}")

            # Report info
            if result.get("report_id"):
                st.divider()
                st.caption(f"Report ID: {result.get('report_id')}")
                st.caption(f"Generated: {result.get('generated_at', 'N/A')}")

        elif not st.session_state.error_message:
            st.info("Enter code and click 'Start Analysis' to begin.")

    # Real-time trace
    if show_trace and st.session_state.trace_events:
        st.divider()
        st.header("Agent Activity Log")

        for event in st.session_state.trace_events:
            agent = event.get("agent", "unknown")
            agent_colors = {
                "orchestrator": "🟦",
                "audit_orchestrator": "🟦",
                "code_analyzer": "🟩",
                "audit_agent": "🟩",
                "rule_matcher": "🟨",
                "rule_evaluator": "🟨",
                "report_generator": "🟪",
                "code_reader": "🟧",
                "pdf_reader": "🟧",
            }
            color = agent_colors.get(agent, "⬜")
            event_type = event.get("event_type", "")
            message = event.get("message", "")
            st.text(f"{color} [{agent}] {event_type}: {message}")

    # Pending reviews section
    if st.session_state.pending_reviews:
        st.divider()
        st.header("Pending Reviews (HITL)")

        for review_id in st.session_state.pending_reviews:
            with st.expander(f"Review: {review_id}"):
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Approve", key=f"approve_{review_id}"):
                        try:
                            loop = asyncio.new_event_loop()
                            result = loop.run_until_complete(
                                submit_review(review_id, "approve", "Approved via UI")
                            )
                            st.success("Review approved")
                            st.session_state.pending_reviews.remove(review_id)
                        except Exception as e:
                            st.error(f"Failed: {e}")
                        finally:
                            loop.close()
                with col2:
                    if st.button("Reject", key=f"reject_{review_id}"):
                        try:
                            loop = asyncio.new_event_loop()
                            result = loop.run_until_complete(
                                submit_review(review_id, "reject", "Rejected via UI")
                            )
                            st.warning("Review rejected")
                            st.session_state.pending_reviews.remove(review_id)
                        except Exception as e:
                            st.error(f"Failed: {e}")
                        finally:
                            loop.close()

    # Footer
    st.divider()
    st.caption("Kompline v0.1.0 | Algorithm Fairness Self-Assessment Automation System")


if __name__ == "__main__":
    main()
