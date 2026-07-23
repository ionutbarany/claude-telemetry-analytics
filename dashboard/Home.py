"""Claude Telemetry Analytics dashboard — consumes FastAPI analytics endpoints."""

from __future__ import annotations

from typing import Any, TypedDict

import plotly.express as px
import requests
import streamlit as st

PAGE_TITLE = "Claude Telemetry Analytics"
DEFAULT_API_BASE_URL = "http://api:8000"
REQUEST_TIMEOUT_SECONDS = 30
CACHE_TTL_SECONDS = 60
TOP_USERS_LIMIT = 10


class OverviewMetrics(TypedDict):
    """Platform-wide aggregate metrics from ``GET /analytics/overview``."""

    total_requests: int
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    avg_latency_ms: float
    unique_users: int


class ModelMetrics(TypedDict):
    """Per-model rollup from ``GET /analytics/models``."""

    model_name: str
    requests: int
    total_cost_usd: float
    avg_latency_ms: float


class TopUserMetrics(TypedDict):
    """Per-user cost rollup from ``GET /analytics/top-users``."""

    user_email: str
    total_cost_usd: float
    total_tokens: int


def configure_page() -> None:
    """Apply global Streamlit page settings."""
    st.set_page_config(
        page_title=PAGE_TITLE,
        layout="wide",
    )


def _analytics_url(base_url: str, path: str) -> str:
    """Build a fully qualified analytics endpoint URL."""
    return f"{base_url.rstrip('/')}{path}"


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def fetch_overview(base_url: str) -> OverviewMetrics:
    """Fetch platform-wide KPI totals from the analytics API."""
    response = requests.get(
        _analytics_url(base_url, "/analytics/overview"),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def fetch_models(base_url: str) -> list[ModelMetrics]:
    """Fetch per-model usage and cost rollups from the analytics API."""
    response = requests.get(
        _analytics_url(base_url, "/analytics/models"),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def fetch_top_users(base_url: str, limit: int) -> list[TopUserMetrics]:
    """Fetch the highest-spending users ranked by total cost."""
    response = requests.get(
        _analytics_url(base_url, "/analytics/top-users"),
        params={"limit": limit},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def render_sidebar() -> str:
    """Render API configuration controls and return the active base URL."""
    st.sidebar.title("Settings")
    base_url = st.sidebar.text_input(
        label="API base URL",
        value=DEFAULT_API_BASE_URL,
        help="FastAPI service root URL. Use http://api:8000 inside Docker.",
    )

    if st.sidebar.button("Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.caption(f"Cached responses expire after {CACHE_TTL_SECONDS} seconds.")
    return base_url


def _format_currency(value: float) -> str:
    """Format a USD amount for display in KPI cards."""
    return f"${value:,.2f}"


def _format_integer(value: int) -> str:
    """Format an integer with thousands separators."""
    return f"{value:,}"


def render_kpi_cards(overview: OverviewMetrics) -> None:
    """Display headline KPI metrics in a two-row grid."""
    row_one_col, row_two_col, row_three_col = st.columns(3)
    row_four_col, row_five_col, row_six_col = st.columns(3)

    with row_one_col:
        st.metric(
            label="Total Requests",
            value=_format_integer(overview["total_requests"]),
        )

    with row_two_col:
        st.metric(
            label="Total Cost",
            value=_format_currency(overview["total_cost_usd"]),
        )

    with row_three_col:
        st.metric(
            label="Input Tokens",
            value=_format_integer(overview["total_input_tokens"]),
        )

    with row_four_col:
        st.metric(
            label="Output Tokens",
            value=_format_integer(overview["total_output_tokens"]),
        )

    with row_five_col:
        st.metric(
            label="Avg Latency",
            value=f"{overview['avg_latency_ms']:,.1f} ms",
        )

    with row_six_col:
        st.metric(
            label="Unique Users",
            value=_format_integer(overview["unique_users"]),
        )


def render_cost_by_model_chart(models: list[ModelMetrics]) -> None:
    """Render a bar chart of total cost grouped by model."""
    if not models:
        st.info("No model usage data available.")
        return

    figure = px.bar(
        models,
        x="model_name",
        y="total_cost_usd",
        title="Total Cost by Model",
        labels={"model_name": "Model", "total_cost_usd": "Total Cost (USD)"},
        color="model_name",
    )
    figure.update_layout(showlegend=False, xaxis_title="Model", yaxis_title="Cost (USD)")
    st.plotly_chart(figure, use_container_width=True)


def render_requests_by_model_chart(models: list[ModelMetrics]) -> None:
    """Render a bar chart of request counts grouped by model."""
    if not models:
        st.info("No model usage data available.")
        return

    figure = px.bar(
        models,
        x="model_name",
        y="requests",
        title="Request Count by Model",
        labels={"model_name": "Model", "requests": "Requests"},
        color="model_name",
    )
    figure.update_layout(showlegend=False, xaxis_title="Model", yaxis_title="Requests")
    st.plotly_chart(figure, use_container_width=True)


def render_top_users_table(top_users: list[TopUserMetrics]) -> None:
    """Render a sortable table of the highest-spending users."""
    if not top_users:
        st.info("No user cost data available.")
        return

    rows: list[dict[str, Any]] = [
        {
            "User Email": user["user_email"],
            "Total Cost (USD)": user["total_cost_usd"],
            "Total Tokens": user["total_tokens"],
        }
        for user in top_users
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def load_dashboard_data(base_url: str) -> tuple[
    OverviewMetrics | None,
    list[ModelMetrics] | None,
    list[TopUserMetrics] | None,
]:
    """Load all dashboard datasets, surfacing API failures via ``st.error``."""
    overview: OverviewMetrics | None = None
    models: list[ModelMetrics] | None = None
    top_users: list[TopUserMetrics] | None = None

    try:
        overview = fetch_overview(base_url)
    except requests.RequestException as exc:
        st.error(f"Failed to load overview metrics: {exc}")

    try:
        models = fetch_models(base_url)
    except requests.RequestException as exc:
        st.error(f"Failed to load model analytics: {exc}")

    try:
        top_users = fetch_top_users(base_url, TOP_USERS_LIMIT)
    except requests.RequestException as exc:
        st.error(f"Failed to load top users: {exc}")

    return overview, models, top_users


def main() -> None:
    """Render the telemetry analytics overview dashboard."""
    configure_page()
    base_url = render_sidebar()

    st.title(PAGE_TITLE)
    st.markdown(
        "Live platform metrics sourced from the FastAPI analytics layer. "
        "Explore request volume, token usage, cost, and top spenders."
    )

    overview, models, top_users = load_dashboard_data(base_url)

    if overview is not None:
        st.subheader("Key metrics")
        render_kpi_cards(overview)

    if models is not None:
        cost_col, requests_col = st.columns(2)
        with cost_col:
            render_cost_by_model_chart(models)
        with requests_col:
            render_requests_by_model_chart(models)

    if top_users is not None:
        st.subheader(f"Top {TOP_USERS_LIMIT} Users by Cost")
        render_top_users_table(top_users)

    st.divider()
    st.caption("Dashboard powered by FastAPI + PostgreSQL + Streamlit.")


if __name__ == "__main__":
    main()
