"""Batch insert orchestration for ETL load stages."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import TypeVar

INSERT_BATCH_SIZE = 1000

T = TypeVar("T")


def chunk_sequence(items: Sequence[T], batch_size: int = INSERT_BATCH_SIZE) -> Iterator[Sequence[T]]:
    """Yield fixed-size slices from ``items`` for batched database writes.

    Args:
        items: Sequence to partition.
        batch_size: Maximum number of elements per batch.

    Yields:
        Non-empty slices of ``items``.
    """
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")

    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]
