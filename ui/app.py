"""Streamlit demo UI for Kompline."""

import asyncio

import httpx
import streamlit as st

from kompline.demo_data import register_demo_compliances

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


async def analyze_via_api(
    source_code: str,
    require_review: bool = True,
    compliance_ids: list[str] | None = None,
    use_llm: bool = True,
) -> dict:
    """Call the FastAPI backend for analysis."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{API_URL}/analyze",
            json={
                "source_code": source_code,
                "compliance_ids": compliance_ids,
                "use_llm": use_llm,
                "require_review": require_review,
            },
        )
        response.raise_for_status()
        return response.json()


async def analyze_local(
    source_code: str,
    require_review: bool = True,
    compliance_ids: list[str] | None = None,
    use_llm: bool = True,
) -> dict:
    """Run analysis locally without API."""
    try:
        from kompline.runner import KomplineRunner
        runner = KomplineRunner()
        result = await runner.analyze(
            source_code=source_code,
            compliance_ids=compliance_ids,
            use_llm=use_llm,
            require_review=require_review,
        )
        pending_reviews = []
        payload = result.get("result") or {}
        for rel in payload.get("relations", []):
            for finding in rel.get("findings", []):
                if finding.get("requires_human_review"):
                    pending_reviews.append(finding)

        return {
            "success": result.get("success", False),
            "result": result.get("result"),
            "report": result.get("report"),
            "report_markdown": result.get("report_markdown"),
            "pending_reviews": pending_reviews,
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


def run_analysis(
    source_code: str,
    require_review: bool,
    use_api: bool,
    compliance_ids: list[str] | None,
    use_llm: bool,
):
    """Run the analysis synchronously."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        if use_api:
            return loop.run_until_complete(
                analyze_via_api(
                    source_code,
                    require_review=require_review,
                    compliance_ids=compliance_ids,
                    use_llm=use_llm,
                )
            )
        return loop.run_until_complete(
            analyze_local(
                source_code,
                require_review=require_review,
                compliance_ids=compliance_ids,
                use_llm=use_llm,
            )
        )
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

        use_llm = st.checkbox("Use LLM Evaluation", value=True)
        require_review = st.checkbox("Enable Human-in-the-Loop", value=True)
        show_trace = st.checkbox("Show Real-time Logs", value=True)

        st.divider()

        st.header("Compliance Selection")
        compliance_ids = register_demo_compliances()
        selected_compliances = st.multiselect(
            "Apply compliances",
            options=compliance_ids,
            default=["byeolji5-fairness"],
        )

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

        uploaded = st.file_uploader("Upload a .py file", type=["py"])
        if uploaded is not None:
            st.session_state.code_input = uploaded.read().decode("utf-8")

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
                        selected_compliances,
                        use_llm,
                    )

                    if result.get("success"):
                        st.session_state.analysis_result = result
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
            payload = st.session_state.analysis_result
            summary = payload.get("result") or {}

            if summary:
                status = "COMPLIANT" if summary.get("is_compliant") else "NON_COMPLIANT"
            else:
                status = "UNKNOWN"

            if status == "COMPLIANT":
                st.success("COMPLIANT - Regulation Satisfied")
            elif status == "NON_COMPLIANT":
                st.error("NON_COMPLIANT - Violations Found")
            else:
                st.info("Status: UNKNOWN")

            cols = st.columns(3)
            cols[0].metric("PASS", summary.get("total_passed", 0))
            cols[1].metric(
                "FAIL",
                summary.get("total_failed", 0),
                delta=None if summary.get("total_failed", 0) == 0 else f"-{summary.get('total_failed', 0)}",
            )
            cols[2].metric("REVIEW", summary.get("total_review", 0))

            st.divider()

            st.subheader("Detailed Findings")
            for relation in summary.get("relations", []):
                title = f"{relation['compliance_id']} × {relation['artifact_id']}"
                with st.expander(title):
                    for finding in relation.get("findings", []):
                        status_icon = {
                            "pass": "✅",
                            "fail": "❌",
                            "review": "⚠️",
                            "not_applicable": "➖",
                        }.get(finding.get("status"), "❓")
                        st.write(f"{status_icon} {finding.get('rule_id', 'Unknown')}")
                        st.write(f"**Status**: {finding.get('status', 'unknown')}")
                        st.write(f"**Confidence**: {finding.get('confidence', 0):.0%}")
                        st.write(f"**Reasoning**: {finding.get('reasoning', '')}")
                        if finding.get("recommendation"):
                            st.warning(f"**Recommendation**: {finding['recommendation']}")

            if payload.get("report_markdown"):
                st.divider()
                st.subheader("Report")
                st.markdown(payload.get("report_markdown", ""))

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
        for finding in st.session_state.pending_reviews:
            with st.expander(f"Review Needed: {finding.get('rule_id', 'Unknown')}"):
                st.write(f"Status: {finding.get('status')}")
                st.write(f"Confidence: {finding.get('confidence', 0):.0%}")
                st.write(f"Reasoning: {finding.get('reasoning', '')}")

    # Footer
    st.divider()
    st.caption("Kompline v0.1.0 | Algorithm Fairness Self-Assessment Automation System")


if __name__ == "__main__":
    main()
