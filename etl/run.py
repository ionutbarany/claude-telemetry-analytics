"""CLI entry point for running the ETL pipeline."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path

from etl.parsers.events import TelemetryEvent, parse_event
from etl.parsers.jsonl import read_jsonl

logger = logging.getLogger(__name__)


def configure_logging(level: str) -> None:
    """Configure root logging for CLI output."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )


def extract_events_from_record(record: dict) -> list[dict]:
    """Extract telemetry events from a JSONL record or CloudWatch-style batch."""
    log_events = record.get("logEvents")
    if not isinstance(log_events, list):
        if "body" in record:
            return [record]
        return []

    events: list[dict] = []
    for log_event in log_events:
        if not isinstance(log_event, dict):
            continue
        message = log_event.get("message")
        if not isinstance(message, str):
            continue
        try:
            parsed = json.loads(message)
        except json.JSONDecodeError:
            logger.warning("Skipping log event with invalid JSON message payload")
            continue
        if isinstance(parsed, dict):
            events.append(parsed)
    return events


def count_log_events(record: dict) -> int:
    """Return the number of log events represented by one JSONL record."""
    log_events = record.get("logEvents")
    if isinstance(log_events, list):
        return len(log_events)
    return 1 if "body" in record else 0


def collect_sample_keys(events: Sequence[dict], key: str, limit: int = 12) -> list[str]:
    """Collect a sorted sample of nested keys from event dictionaries."""
    keys: set[str] = set()
    for event in events:
        nested = event.get(key)
        if isinstance(nested, dict):
            keys.update(str(nested_key) for nested_key in nested)
        if len(keys) >= limit:
            break
    return sorted(keys)[:limit]


def take_records(path: Path, limit: int) -> list[dict]:
    """Read up to ``limit`` JSONL records from ``path``."""
    records: list[dict] = []
    for index, record in enumerate(read_jsonl(path), start=1):
        records.append(record)
        if index >= limit:
            break
    return records


def read_first_record(path: Path) -> dict | None:
    """Read the first JSONL record from ``path``, if any."""
    for record in read_jsonl(path):
        return record
    return None


def prepare_record_for_parser(record: dict) -> dict:
    """Adapt a JSONL record into the shape expected by ``parse_event``."""
    log_events = record.get("logEvents")
    if isinstance(log_events, list) and log_events:
        first_event = log_events[0]
        if isinstance(first_event, dict) and isinstance(first_event.get("attributes"), dict):
            return record

    attributes = record.get("attributes")
    if isinstance(attributes, dict):
        resource = record.get("resource")
        if not isinstance(resource, dict):
            resource = {}
        return {
            "logEvents": [{"attributes": attributes}],
            "resource": resource,
        }

    raise ValueError("Record does not contain parseable telemetry attributes")


def format_telemetry_event(event: TelemetryEvent) -> str:
    """Pretty-print a parsed telemetry event with all extracted fields."""
    raw_json = json.dumps(event.raw, indent=2, sort_keys=True)
    indented_raw = "\n".join(f"  {line}" for line in raw_json.splitlines())

    return "\n".join(
        [
            "TelemetryEvent(",
            f"  event_name={event.event_name!r},",
            f"  event_ts={event.event_ts.isoformat()!r},",
            f"  user_email={event.user_email!r},",
            f"  practice={event.practice!r},",
            f"  profile={event.profile!r},",
            f"  model_name={event.model_name!r},",
            f"  input_tokens={event.input_tokens},",
            f"  output_tokens={event.output_tokens},",
            f"  cache_read_tokens={event.cache_read_tokens},",
            f"  cache_creation_tokens={event.cache_creation_tokens},",
            f"  cost_usd={event.cost_usd},",
            f"  duration_ms={event.duration_ms!r},",
            "  raw=",
            indented_raw,
            ")",
        ]
    )


def format_inspect_report(path: Path, records: Sequence[dict]) -> str:
    """Build a human-readable inspection report for sampled JSONL records."""
    if not records:
        return f"No records found in {path}"

    all_events: list[dict] = []
    batch_sizes: list[int] = []
    body_values: set[str] = set()

    for record in records:
        batch_size = count_log_events(record)
        batch_sizes.append(batch_size)
        events = extract_events_from_record(record)
        all_events.extend(events)
        for event in events:
            body = event.get("body")
            if isinstance(body, str):
                body_values.add(body)

    attribute_keys = collect_sample_keys(all_events, "attributes")
    resource_keys = collect_sample_keys(all_events, "resource")

    lines = [
        f"Input: {path}",
        f"Records sampled: {len(records)}",
        "",
        "logEvents per batch:",
    ]
    for index, batch_size in enumerate(batch_sizes, start=1):
        lines.append(f"  record {index}: {batch_size}")

    lines.extend(
        [
            "",
            "Event body values:",
        ]
    )
    if body_values:
        for body in sorted(body_values):
            lines.append(f"  - {body}")
    else:
        lines.append("  (none found)")

    lines.extend(["", "Sample attribute keys:"])
    if attribute_keys:
        for key in attribute_keys:
            lines.append(f"  - {key}")
    else:
        lines.append("  (none found)")

    lines.extend(["", "Sample resource keys:"])
    if resource_keys:
        for key in resource_keys:
            lines.append(f"  - {key}")
    else:
        lines.append("  (none found)")

    return "\n".join(lines)


def cmd_sample(args: argparse.Namespace) -> int:
    """Parse and pretty-print the first telemetry record in a JSONL file."""
    input_path: Path = args.input
    if not input_path.is_file():
        logger.error("Input file does not exist: %s", input_path)
        return 1

    logger.info("Sampling first record from %s", input_path)
    record = read_first_record(input_path)
    if record is None:
        logger.error("No records found in %s", input_path)
        return 1

    try:
        prepared = prepare_record_for_parser(record)
        event = parse_event(prepared)
    except (TypeError, ValueError) as exc:
        logger.error("Failed to parse first record: %s", exc)
        return 1

    print(format_telemetry_event(event))
    return 0


API_REQUEST_EVENT_NAME = "api_request"


def parse_jsonl_events(path: Path) -> tuple[int, list[TelemetryEvent]]:
    """Read and parse all telemetry events from a JSONL file.

    Args:
        path: Path to a telemetry JSONL file.

    Returns:
        Tuple of ``(records_read, parsed_events)``. Records that fail parsing are
        logged and skipped.
    """
    records_read = 0
    parsed_events: list[TelemetryEvent] = []

    for record in read_jsonl(path):
        records_read += 1
        try:
            prepared = prepare_record_for_parser(record)
            parsed_events.append(parse_event(prepared))
        except (TypeError, ValueError) as exc:
            logger.warning("Skipping record %s in %s: %s", records_read, path, exc)

    return records_read, parsed_events


def cmd_load(args: argparse.Namespace) -> int:
    """Load parsed API request telemetry events into PostgreSQL."""
    input_path: Path = args.input
    employees_path: Path | None = args.employees
    if not input_path.is_file():
        logger.error("Input file does not exist: %s", input_path)
        return 1

    logger.info("Loading telemetry events from %s", input_path)
    records_read, parsed_events = parse_jsonl_events(input_path)
    api_request_events = [
        event for event in parsed_events if event.event_name == API_REQUEST_EVENT_NAME
    ]

    from etl.loaders.postgres import insert_api_requests, sync_dim_users_from_events
    from etl.transformers.enrich import employees_by_email, load_employees_csv

    employee_records = []
    if employees_path is not None:
        if not employees_path.is_file():
            logger.error("Employee file does not exist: %s", employees_path)
            return 1
        try:
            employee_records = load_employees_csv(employees_path)
        except (FileNotFoundError, ValueError) as exc:
            logger.error("Failed to load employees.csv: %s", exc)
            return 1

    employee_lookup = employees_by_email(employee_records)

    try:
        users_upserted = sync_dim_users_from_events(
            parsed_events,
            employee_lookup,
        )
        inserted = insert_api_requests(api_request_events)
    except Exception:
        logger.error("Failed to load telemetry data into PostgreSQL")
        return 1

    print(f"Records read: {records_read}")
    print(f"Events parsed: {len(parsed_events)}")
    print(f"dim_users rows upserted: {users_upserted}")
    print(f"api_request events inserted: {inserted}")
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    """Inspect the first records in a telemetry JSONL file."""
    input_path: Path = args.input
    if not input_path.is_file():
        logger.error("Input file does not exist: %s", input_path)
        return 1

    logger.info("Inspecting first %s records from %s", args.limit, input_path)
    records = take_records(input_path, args.limit)
    report = format_inspect_report(input_path, records)
    print(report)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI argument parser."""
    parser = argparse.ArgumentParser(description="Run telemetry ETL commands.")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Inspect the structure of a telemetry JSONL file.",
    )
    inspect_parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to a telemetry_logs.jsonl file.",
    )
    inspect_parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Number of JSONL records to sample.",
    )
    inspect_parser.set_defaults(handler=cmd_inspect)

    sample_parser = subparsers.add_parser(
        "sample",
        help="Parse and display the first telemetry record.",
    )
    sample_parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to a telemetry_logs.jsonl file.",
    )
    sample_parser.set_defaults(handler=cmd_sample)

    load_parser = subparsers.add_parser(
        "load",
        help="Parse telemetry JSONL and load api_request events into PostgreSQL.",
    )
    load_parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to a telemetry_logs.jsonl file.",
    )
    load_parser.add_argument(
        "--employees",
        type=Path,
        default=None,
        help="Optional path to employees.csv for dim_users enrichment.",
    )
    load_parser.set_defaults(handler=cmd_load)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse CLI arguments and dispatch to the selected command."""
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.log_level)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 1
    return int(handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
