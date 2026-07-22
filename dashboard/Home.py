"""Claude Telemetry Analytics dashboard landing page."""

import streamlit as st

PAGE_TITLE = "Claude Telemetry Analytics"
NAV_ITEMS = ("Overview", "Users", "Sessions", "Tokens", "Insights")

PLANNED_ANALYTICS = (
    "Session volume and duration trends over time",
    "Token usage breakdown by model and user",
    "Estimated API cost and spend forecasting",
    "Tool invocation success rates and latency",
    "Error rates and status-code distribution",
    "User activity and prompt frequency patterns",
)


def configure_page() -> None:
    """Apply global Streamlit page settings."""
    st.set_page_config(
        page_title=PAGE_TITLE,
        layout="wide",
    )


def render_sidebar() -> None:
    """Render placeholder navigation in the sidebar."""
    st.sidebar.title("Navigation")
    st.sidebar.radio(
        label="Go to",
        options=NAV_ITEMS,
        index=0,
        label_visibility="collapsed",
    )


def render_kpi_cards() -> None:
    """Display headline KPI placeholders in a three-column layout."""
    total_sessions_col, total_tokens_col, estimated_cost_col = st.columns(3)

    with total_sessions_col:
        st.metric(label="Total Sessions", value="—", help="Aggregate session count")

    with total_tokens_col:
        st.metric(label="Total Tokens", value="—", help="Input and output tokens combined")

    with estimated_cost_col:
        st.metric(label="Estimated Cost", value="—", help="USD estimate from token usage")


def render_planned_analytics() -> None:
    """List analytics capabilities planned for future dashboard pages."""
    st.subheader("Planned analytics")
    st.markdown("\n".join(f"- {item}" for item in PLANNED_ANALYTICS))


def render_footer() -> None:
    """Show attribution for the underlying platform stack."""
    st.divider()
    st.caption("Dashboard powered by FastAPI + PostgreSQL + Streamlit.")


def main() -> None:
    """Render the dashboard landing page."""
    configure_page()
    render_sidebar()

    st.title(PAGE_TITLE)
    st.markdown(
        "A production-style telemetry analytics platform for Claude Code events. "
        "Ingest OpenTelemetry data, persist aggregates in PostgreSQL, expose "
        "queryable APIs, and explore usage, cost, and reliability through "
        "interactive dashboards."
    )

    st.subheader("Key metrics")
    render_kpi_cards()

    render_planned_analytics()
    render_footer()


if __name__ == "__main__":
    main()
