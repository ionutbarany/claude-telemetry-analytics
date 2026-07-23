#!/usr/bin/env python3
"""Generate synthetic employees.csv and telemetry_logs.jsonl for local development."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

MODELS: dict[str, dict[str, float | int]] = {
    "claude-haiku-4-5-20251001": {
        "weight": 362,
        "avg_cost": 0.0033,
        "cost_std": 0.005,
        "avg_duration_ms": 5330,
        "duration_std": 4000,
        "avg_input_tokens": 860,
        "input_std": 1200,
        "avg_output_tokens": 105,
        "output_std": 150,
        "avg_cache_read": 7431,
        "cache_read_std": 15000,
        "avg_cache_create": 941,
        "cache_create_std": 2000,
    },
    "claude-opus-4-6": {
        "weight": 203,
        "avg_cost": 0.071,
        "cost_std": 0.08,
        "avg_duration_ms": 10230,
        "duration_std": 8000,
        "avg_input_tokens": 263,
        "input_std": 500,
        "avg_output_tokens": 454,
        "output_std": 400,
        "avg_cache_read": 73099,
        "cache_read_std": 50000,
        "avg_cache_create": 3149,
        "cache_create_std": 5000,
    },
    "claude-sonnet-4-5-20250929": {
        "weight": 155,
        "avg_cost": 0.062,
        "cost_std": 0.07,
        "avg_duration_ms": 11886,
        "duration_std": 9000,
        "avg_input_tokens": 83,
        "input_std": 200,
        "avg_output_tokens": 516,
        "output_std": 500,
        "avg_cache_read": 68556,
        "cache_read_std": 50000,
        "avg_cache_create": 6483,
        "cache_create_std": 8000,
    },
    "claude-sonnet-4-6": {
        "weight": 21,
        "avg_cost": 0.066,
        "cost_std": 0.07,
        "avg_duration_ms": 9914,
        "duration_std": 8000,
        "avg_input_tokens": 142,
        "input_std": 300,
        "avg_output_tokens": 460,
        "output_std": 400,
        "avg_cache_read": 70715,
        "cache_read_std": 50000,
        "avg_cache_create": 2905,
        "cache_create_std": 5000,
    },
}

TOOLS: dict[str, int] = {
    "Read": 190,
    "Bash": 176,
    "Edit": 79,
    "Grep": 47,
    "Glob": 29,
    "Write": 18,
    "TodoWrite": 16,
    "Task": 11,
}

TOOL_SUCCESS_RATES: dict[str, float] = {
    "Read": 0.986,
    "Bash": 0.933,
    "Edit": 0.99,
    "Grep": 0.99,
    "Glob": 0.99,
    "Write": 0.99,
    "TodoWrite": 0.99,
    "Task": 0.99,
}

TOOL_AVG_DURATIONS: dict[str, int] = {
    "Read": 34,
    "Bash": 5169,
    "Edit": 1817,
    "Grep": 474,
    "Glob": 750,
    "Write": 349,
    "TodoWrite": 17,
    "Task": 476282,
}

API_ERRORS: list[tuple[str, str, int]] = [
    ("Request was aborted.", "undefined", 44),
    ("This request would exceed your account's rate limit.", "429", 19),
    ("Internal server error", "500", 4),
    ("OAuth token has expired.", "401", 2),
]

PRACTICES: tuple[str, ...] = (
    "Platform Engineering",
    "Data Engineering",
    "ML Engineering",
    "Backend Engineering",
    "Frontend Engineering",
)

LOCATIONS: tuple[str, ...] = (
    "United States",
    "Germany",
    "United Kingdom",
    "Poland",
    "Canada",
)

LEVELS: list[tuple[str, int]] = [
    ("L1", 2),
    ("L2", 5),
    ("L3", 10),
    ("L4", 18),
    ("L5", 25),
    ("L6", 20),
    ("L7", 10),
    ("L8", 5),
    ("L9", 3),
    ("L10", 2),
]

FIRST_NAMES: tuple[str, ...] = (
    "alex",
    "jordan",
    "casey",
    "taylor",
    "morgan",
    "riley",
    "harper",
    "kai",
    "sam",
    "river",
)

LAST_NAMES: tuple[str, ...] = (
    "chen",
    "patel",
    "kim",
    "garcia",
    "smith",
    "johnson",
    "lee",
    "williams",
    "brown",
    "jones",
)

TERMINAL_TYPES: list[tuple[str, int]] = [
    ("vscode", 40),
    ("cursor", 25),
    ("iTerm.app", 15),
    ("pycharm", 10),
    ("WarpTerminal", 10),
]

APP_VERSIONS: list[tuple[str, int]] = [
    ("2.1.50", 151),
    ("2.1.45", 108),
    ("2.1.39", 159),
    ("2.1.56", 64),
]

OS_CONFIGS: list[tuple[dict[str, str], int]] = [
    ({"arch": "arm64", "os_type": "darwin", "os_version": "24.6.0"}, 60),
    ({"arch": "x86_64", "os_type": "linux", "os_version": "6.1.0"}, 20),
    ({"arch": "x86_64", "os_type": "windows", "os_version": "10.0.26200"}, 20),
]

EMPLOYEE_FIELDS: tuple[str, ...] = ("email", "full_name", "practice", "level", "location")


def weighted_choice(items: Sequence[tuple[T, int]]) -> T:
    """Return one item chosen according to integer weights."""
    choices, weights = zip(*items)
    return random.choices(choices, weights=weights, k=1)[0]


def positive_normal(mean: float, std: float, min_val: float = 0.0) -> float:
    """Sample a positive value from a normal distribution."""
    return max(min_val, random.gauss(mean, std))


def format_event_timestamp(timestamp: datetime) -> str:
    """Format an event timestamp in Claude Code OTel log style."""
    millis = timestamp.microsecond // 1000
    return timestamp.strftime("%Y-%m-%dT%H:%M:%S.") + f"{millis:03d}Z"


def generate_employee(existing_emails: set[str], organization_id: str) -> dict[str, str]:
    """Create one synthetic employee row and backing telemetry identity fields."""
    while True:
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        email = f"{first}.{last}@example.com"
        if email not in existing_emails:
            break

    existing_emails.add(email)
    full_name = f"{first.capitalize()} {last.capitalize()}"
    hostname = f"{first}-laptop.local"
    profile = f"{first}.{last}"

    return {
        "email": email,
        "full_name": full_name,
        "practice": random.choice(PRACTICES),
        "level": weighted_choice(LEVELS),
        "location": random.choice(LOCATIONS),
        "account_uuid": str(uuid.uuid4()),
        "user_id": uuid.uuid5(uuid.NAMESPACE_DNS, email).hex,
        "organization_id": organization_id,
        "hostname": hostname,
        "profile": profile,
        "terminal": weighted_choice(TERMINAL_TYPES),
        "app_version": weighted_choice(APP_VERSIONS),
        "os_config": weighted_choice([(cfg, weight) for cfg, weight in OS_CONFIGS]),
    }


def make_resource(user: dict[str, str]) -> dict[str, str]:
    """Build the OTel resource block for a telemetry event."""
    os_config = user["os_config"]
    return {
        "host.arch": os_config["arch"],
        "host.name": user["hostname"],
        "os.type": os_config["os_type"],
        "os.version": os_config["os_version"],
        "service.name": "claude-code",
        "service.version": user["app_version"],
        "user.email": user["email"],
        "user.practice": user["practice"],
        "user.profile": user["profile"],
    }


def make_common_attributes(
    user: dict[str, str],
    session_id: str,
    timestamp: datetime,
) -> dict[str, str]:
    """Build attributes shared across all Claude Code telemetry events."""
    return {
        "event.timestamp": format_event_timestamp(timestamp),
        "organization.id": user["organization_id"],
        "session.id": session_id,
        "terminal.type": user["terminal"],
        "user.account_uuid": user["account_uuid"],
        "user.email": user["email"],
        "user.id": user["user_id"],
        "app.version": user["app_version"],
    }


def generate_api_request_event(
    user: dict[str, str],
    session_id: str,
    timestamp: datetime,
) -> dict[str, Any]:
    """Generate a claude_code.api_request event with token and cost metrics."""
    model_name = weighted_choice([(name, int(stats["weight"])) for name, stats in MODELS.items()])
    model = MODELS[model_name]

    input_tokens = max(0, int(positive_normal(float(model["avg_input_tokens"]), float(model["input_std"]))))
    output_tokens = max(1, int(positive_normal(float(model["avg_output_tokens"]), float(model["output_std"]))))
    cache_read = max(0, int(positive_normal(float(model["avg_cache_read"]), float(model["cache_read_std"]))))
    cache_create = max(
        0,
        int(positive_normal(float(model["avg_cache_create"]), float(model["cache_create_std"]))),
    )
    cost_usd = round(positive_normal(float(model["avg_cost"]), float(model["cost_std"])), 6)
    duration_ms = max(100, int(positive_normal(float(model["avg_duration_ms"]), float(model["duration_std"]))))

    attributes = make_common_attributes(user, session_id, timestamp)
    attributes.update(
        {
            "event.name": "api_request",
            "model": model_name,
            "input_tokens": str(input_tokens),
            "output_tokens": str(output_tokens),
            "cache_read_tokens": str(cache_read),
            "cache_creation_tokens": str(cache_create),
            "cost_usd": str(cost_usd),
            "duration_ms": str(duration_ms),
        }
    )

    return {
        "body": "claude_code.api_request",
        "attributes": attributes,
        "resource": make_resource(user),
    }


def generate_tool_result_event(
    user: dict[str, str],
    session_id: str,
    timestamp: datetime,
    tool_name: str | None = None,
) -> dict[str, Any]:
    """Generate a claude_code.tool_result event."""
    selected_tool = tool_name or weighted_choice([(name, weight) for name, weight in TOOLS.items()])
    success_rate = TOOL_SUCCESS_RATES.get(selected_tool, 0.95)
    success = random.random() < success_rate
    avg_duration = TOOL_AVG_DURATIONS.get(selected_tool, 1000)
    duration_ms = max(0, int(positive_normal(float(avg_duration), float(avg_duration) * 0.8)))

    attributes = make_common_attributes(user, session_id, timestamp)
    attributes.update(
        {
            "event.name": "tool_result",
            "tool_name": selected_tool,
            "success": str(success).lower(),
            "duration_ms": str(duration_ms),
        }
    )

    return {
        "body": "claude_code.tool_result",
        "attributes": attributes,
        "resource": make_resource(user),
    }


def generate_user_prompt_event(
    user: dict[str, str],
    session_id: str,
    timestamp: datetime,
) -> dict[str, Any]:
    """Generate a claude_code.user_prompt event."""
    prompt_length = max(1, int(random.lognormvariate(4.85, 1.8)))
    attributes = make_common_attributes(user, session_id, timestamp)
    attributes.update(
        {
            "event.name": "user_prompt",
            "prompt_length": str(prompt_length),
            "prompt.id": str(uuid.uuid4()),
        }
    )

    return {
        "body": "claude_code.user_prompt",
        "attributes": attributes,
        "resource": make_resource(user),
    }


def generate_api_error_event(
    user: dict[str, str],
    session_id: str,
    timestamp: datetime,
) -> dict[str, Any]:
    """Generate a claude_code.api_error event."""
    error_message, status_code = weighted_choice(
        [((message, code), weight) for message, code, weight in API_ERRORS]
    )
    model_name = weighted_choice([(name, int(stats["weight"])) for name, stats in MODELS.items()])
    duration_ms = max(50, int(positive_normal(500, 600)))

    attributes = make_common_attributes(user, session_id, timestamp)
    attributes.update(
        {
            "event.name": "api_error",
            "error": error_message,
            "status_code": status_code,
            "model": model_name,
            "duration_ms": str(duration_ms),
        }
    )

    return {
        "body": "claude_code.api_error",
        "attributes": attributes,
        "resource": make_resource(user),
    }


def generate_session_events(
    user: dict[str, str],
    session_id: str,
    session_start: datetime,
) -> list[dict[str, Any]]:
    """Generate a realistic sequence of events for one coding session."""
    events: list[dict[str, Any]] = []
    current_time = session_start
    num_turns = min(max(1, int(random.lognormvariate(1.5, 1.0))), 50)

    for _ in range(num_turns):
        events.append(generate_user_prompt_event(user, session_id, current_time))
        current_time += timedelta(milliseconds=random.randint(100, 2000))

        num_cycles = min(max(1, int(random.lognormvariate(1.0, 0.8))), 20)
        for _ in range(num_cycles):
            api_event = generate_api_request_event(user, session_id, current_time)
            events.append(api_event)
            current_time += timedelta(milliseconds=int(api_event["attributes"]["duration_ms"]))

            if random.random() < 0.012:
                events.append(generate_api_error_event(user, session_id, current_time))
                current_time += timedelta(milliseconds=random.randint(500, 3000))
                retry_event = generate_api_request_event(user, session_id, current_time)
                events.append(retry_event)
                current_time += timedelta(milliseconds=int(retry_event["attributes"]["duration_ms"]))

            num_tools = random.choices([0, 1, 2], weights=[20, 55, 25], k=1)[0]
            for _ in range(num_tools):
                tool_event = generate_tool_result_event(user, session_id, current_time)
                events.append(tool_event)
                current_time += timedelta(milliseconds=int(tool_event["attributes"]["duration_ms"]))

            current_time += timedelta(milliseconds=random.randint(50, 500))

        current_time += timedelta(seconds=random.randint(5, 120))

    return events


def write_employees_csv(output_path: Path, users: Sequence[dict[str, str]]) -> None:
    """Write employee metadata to CSV for ETL enrichment."""
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=EMPLOYEE_FIELDS)
        writer.writeheader()
        for user in users:
            writer.writerow({field: user[field] for field in EMPLOYEE_FIELDS})
    logger.info("Wrote %s employees to %s", len(users), output_path)


def write_telemetry_jsonl(output_path: Path, events: Sequence[dict[str, Any]]) -> None:
    """Write telemetry events as one JSON object per line."""
    with output_path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, separators=(",", ":")) + "\n")
    logger.info("Wrote %s events to %s", len(events), output_path)


def random_session_start(start_date: datetime, days: int) -> datetime:
    """Pick a session start time within the configured date range."""
    day_offset = random.random() * days
    session_day = start_date + timedelta(days=day_offset)
    hour = random.randint(9, 17) if random.random() < 0.7 else random.randint(0, 23)
    return session_day.replace(hour=hour, minute=random.randint(0, 59), second=0, microsecond=0)


def summarize_events(events: Sequence[dict[str, Any]]) -> dict[str, int]:
    """Count generated events by body type."""
    counts: dict[str, int] = {}
    for event in events:
        body = str(event["body"])
        counts[body] = counts.get(body, 0) + 1
    return counts


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for fake data generation."""
    parser = argparse.ArgumentParser(description="Generate synthetic telemetry and employee data.")
    parser.add_argument("--num-users", type=int, default=30, help="Number of synthetic users.")
    parser.add_argument("--num-sessions", type=int, default=500, help="Total coding sessions to simulate.")
    parser.add_argument("--days", type=int, default=30, help="Number of days to span.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/raw"),
        help="Directory for employees.csv and telemetry_logs.jsonl.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible output.")
    return parser.parse_args()


def main() -> None:
    """Generate employees.csv and telemetry_logs.jsonl from CLI arguments."""
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    random.seed(args.seed)

    logger.info(
        "Generating fake data (users=%s, sessions=%s, days=%s, output=%s)",
        args.num_users,
        args.num_sessions,
        args.days,
        args.output_dir,
    )

    organization_id = str(uuid.uuid4())
    existing_emails: set[str] = set()
    users = [generate_employee(existing_emails, organization_id) for _ in range(args.num_users)]

    end_date = datetime.now(timezone.utc).replace(microsecond=0)
    start_date = end_date - timedelta(days=args.days)

    all_events: list[dict[str, Any]] = []
    for session_index in range(args.num_sessions):
        user = random.choice(users)
        session_id = str(uuid.uuid4())
        session_start = random_session_start(start_date, args.days)
        all_events.extend(generate_session_events(user, session_id, session_start))

        if (session_index + 1) % 500 == 0:
            logger.info("Generated %s/%s sessions", session_index + 1, args.num_sessions)

    all_events.sort(key=lambda event: event["attributes"]["event.timestamp"])

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_employees_csv(args.output_dir / "employees.csv", users)
    write_telemetry_jsonl(args.output_dir / "telemetry_logs.jsonl", all_events)

    counts = summarize_events(all_events)
    total_cost = sum(
        float(event["attributes"].get("cost_usd", 0))
        for event in all_events
        if event["body"] == "claude_code.api_request"
    )

    logger.info("Event breakdown: %s", counts)
    logger.info("Total simulated API cost: $%.2f", total_cost)
    logger.info("Date range: %s to %s", start_date.date(), end_date.date())


if __name__ == "__main__":
    main()
