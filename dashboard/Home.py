"""Claude Telemetry Analytics dashboard — consumes FastAPI analytics endpoints."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

import plotly.express as px
import requests
import streamlit as st

PAGE_TITLE = "Claude Telemetry Analytics"
DEFAULT_API_BASE_URL = "http://api:8000"
REQUEST_TIMEOUT_SECONDS = 30
CACHE_TTL_SECONDS = 60
TOP_USERS_LIMIT = 10

Persona = Literal["Executive", "Engineering Manager", "FinOps"]

PERSONA_DESCRIPTIONS: dict[Persona, str] = {
    "Executive": "High-level platform KPIs and daily usage trends for leadership reviews.",
    "Engineering Manager": "Practice and seniority breakdowns to compare team adoption and spend.",
    "FinOps": "Cost concentration by model, user, and practice for budget oversight.",
}


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


class PracticeMetrics(TypedDict):
    """Per-practice rollup from ``GET /analytics/practices``."""

    practice: str
    requests: int
    total_cost_usd: float
    unique_users: int


class LevelMetrics(TypedDict):
    """Per-level rollup from ``GET /analytics/levels``."""

    level: str
    requests: int
    total_cost_usd: float
    unique_users: int


class TrendMetrics(TypedDict):
    """Daily trend point from ``GET /analytics/trends``."""

    event_date: str
    requests: int
    total_cost_usd: float


def configure_page() -> None:
    """Apply global Streamlit page settings."""
    st.set_page_config(
        page_title=PAGE_TITLE,
        layout="wide",
    )


def _analytics_url(base_url: str, path: str) -> str:
    """Build a fully qualified analytics endpoint URL."""
    return f"{base_url.rstrip('/')}{path}"


def _fetch_json(base_url: str, path: str, params: dict[str, Any] | None = None) -> Any:
    """Perform a GET request against the analytics API and return JSON."""
    response = requests.get(
        _analytics_url(base_url, path),
        params=params,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def fetch_overview(base_url: str) -> OverviewMetrics:
    """Fetch platform-wide KPI totals from the analytics API."""
    return _fetch_json(base_url, "/analytics/overview")


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def fetch_models(base_url: str) -> list[ModelMetrics]:
    """Fetch per-model usage and cost rollups from the analytics API."""
    return _fetch_json(base_url, "/analytics/models")


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def fetch_top_users(base_url: str, limit: int) -> list[TopUserMetrics]:
    """Fetch the highest-spending users ranked by total cost."""
    return _fetch_json(base_url, "/analytics/top-users", params={"limit": limit})


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def fetch_practices(base_url: str) -> list[PracticeMetrics]:
    """Fetch practice-level cost and usage rollups."""
    return _fetch_json(base_url, "/analytics/practices")


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def fetch_levels(base_url: str) -> list[LevelMetrics]:
    """Fetch seniority-level cost and usage rollups."""
    return _fetch_json(base_url, "/analytics/levels")


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def fetch_trends(base_url: str) -> list[TrendMetrics]:
    """Fetch daily request and cost trends."""
    return _fetch_json(base_url, "/analytics/trends")


def render_sidebar() -> tuple[str, Persona]:
    """Render sidebar controls and return the API base URL and selected persona."""
    st.sidebar.title("Settings")
    base_url = st.sidebar.text_input(
        label="API base URL",
        value=DEFAULT_API_BASE_URL,
        help="FastAPI service root URL. Use http://api:8000 inside Docker.",
    )

    persona: Persona = st.sidebar.radio(
        label="Persona",
        options=list(PERSONA_DESCRIPTIONS.keys()),
        index=0,
        help="Switch views to match how different stakeholders consume analytics.",
    )
    st.sidebar.caption(PERSONA_DESCRIPTIONS[persona])

    if st.sidebar.button("Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.caption(f"Cached responses expire after {CACHE_TTL_SECONDS} seconds.")
    return base_url, persona


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
        st.metric(label="Total Requests", value=_format_integer(overview["total_requests"]))
    with row_two_col:
        st.metric(label="Total Cost", value=_format_currency(overview["total_cost_usd"]))
    with row_three_col:
        st.metric(label="Input Tokens", value=_format_integer(overview["total_input_tokens"]))
    with row_four_col:
        st.metric(label="Output Tokens", value=_format_integer(overview["total_output_tokens"]))
    with row_five_col:
        st.metric(label="Avg Latency", value=f"{overview['avg_latency_ms']:,.1f} ms")
    with row_six_col:
        st.metric(label="Unique Users", value=_format_integer(overview["unique_users"]))


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


def render_practice_chart(practices: list[PracticeMetrics]) -> None:
    """Render cost by engineering practice."""
    if not practices:
        st.info("No practice enrichment data available. Load employees.csv during ETL.")
        return

    figure = px.bar(
        practices,
        x="practice",
        y="total_cost_usd",
        title="Total Cost by Practice",
        labels={"practice": "Practice", "total_cost_usd": "Total Cost (USD)"},
        color="practice",
    )
    figure.update_layout(showlegend=False)
    st.plotly_chart(figure, use_container_width=True)


def render_level_chart(levels: list[LevelMetrics]) -> None:
    """Render cost by employee level."""
    if not levels:
        st.info("No level enrichment data available. Load employees.csv during ETL.")
        return

    figure = px.bar(
        levels,
        x="level",
        y="total_cost_usd",
        title="Total Cost by Level",
        labels={"level": "Level", "total_cost_usd": "Total Cost (USD)"},
        color="level",
    )
    figure.update_layout(showlegend=False)
    st.plotly_chart(figure, use_container_width=True)


def render_trend_charts(trends: list[TrendMetrics]) -> None:
    """Render daily request and cost trend lines."""
    if not trends:
        st.info("No trend data available.")
        return

    cost_col, request_col = st.columns(2)
    with cost_col:
        figure = px.line(
            trends,
            x="event_date",
            y="total_cost_usd",
            title="Daily Cost Trend",
            labels={"event_date": "Date", "total_cost_usd": "Cost (USD)"},
            markers=True,
        )
        st.plotly_chart(figure, use_container_width=True)

    with request_col:
        figure = px.line(
            trends,
            x="event_date",
            y="requests",
            title="Daily Request Trend",
            labels={"event_date": "Date", "requests": "Requests"},
            markers=True,
        )
        st.plotly_chart(figure, use_container_width=True)


def render_executive_view(base_url: str) -> None:
    """Render leadership-focused KPIs and daily trends."""
    try:
        overview = fetch_overview(base_url)
    except requests.RequestException as exc:
        st.error(f"Failed to load overview metrics: {exc}")
        return

    st.subheader("Key metrics")
    render_kpi_cards(overview)

    try:
        trends = fetch_trends(base_url)
    except requests.RequestException as exc:
        st.error(f"Failed to load trend analytics: {exc}")
        return

    st.subheader("Usage trends")
    render_trend_charts(trends)


def render_engineering_manager_view(base_url: str) -> None:
    """Render practice and seniority views for engineering managers."""
    practice_col, level_col = st.columns(2)

    with practice_col:
        try:
            practices = fetch_practices(base_url)
        except requests.RequestException as exc:
            st.error(f"Failed to load practice analytics: {exc}")
        else:
            st.subheader("Cost by practice")
            render_practice_chart(practices)

    with level_col:
        try:
            levels = fetch_levels(base_url)
        except requests.RequestException as exc:
            st.error(f"Failed to load level analytics: {exc}")
        else:
            st.subheader("Cost by level")
            render_level_chart(levels)

    try:
        models = fetch_models(base_url)
    except requests.RequestException as exc:
        st.error(f"Failed to load model analytics: {exc}")
    else:
        st.subheader("Model adoption")
        render_requests_by_model_chart(models)


def render_finops_view(base_url: str) -> None:
    """Render cost concentration views for finance and platform owners."""
    try:
        overview = fetch_overview(base_url)
    except requests.RequestException as exc:
        st.error(f"Failed to load overview metrics: {exc}")
        overview = None

    if overview is not None:
        fin_col_one, fin_col_two, fin_col_three = st.columns(3)
        with fin_col_one:
            st.metric("Total Spend", _format_currency(overview["total_cost_usd"]))
        with fin_col_two:
            st.metric("Billable Requests", _format_integer(overview["total_requests"]))
        with fin_col_three:
            st.metric("Active Users", _format_integer(overview["unique_users"]))

    model_col, practice_col = st.columns(2)
    with model_col:
        try:
            models = fetch_models(base_url)
        except requests.RequestException as exc:
            st.error(f"Failed to load model analytics: {exc}")
        else:
            st.subheader("Spend by model")
            render_cost_by_model_chart(models)

    with practice_col:
        try:
            practices = fetch_practices(base_url)
        except requests.RequestException as exc:
            st.error(f"Failed to load practice analytics: {exc}")
        else:
            st.subheader("Spend by practice")
            render_practice_chart(practices)

    try:
        top_users = fetch_top_users(base_url, TOP_USERS_LIMIT)
    except requests.RequestException as exc:
        st.error(f"Failed to load top users: {exc}")
    else:
        st.subheader(f"Top {TOP_USERS_LIMIT} Users by Cost")
        render_top_users_table(top_users)


def main() -> None:
    """Render the telemetry analytics dashboard for the selected persona."""
    configure_page()
    base_url, persona = render_sidebar()

    st.title(PAGE_TITLE)
    st.markdown(
        "Live platform metrics sourced from the FastAPI analytics layer. "
        "Switch personas in the sidebar to match your stakeholder view."
    )

    if persona == "Executive":
        render_executive_view(base_url)
    elif persona == "Engineering Manager":
        render_engineering_manager_view(base_url)
    else:
        render_finops_view(base_url)

    st.divider()
    st.caption("Dashboard powered by FastAPI + PostgreSQL + Streamlit.")


if __name__ == "__main__":
    main()
