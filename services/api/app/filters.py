from sqlalchemy import Select, or_
from typing import Any, Optional
from datetime import datetime, timezone
from fastapi import HTTPException


def apply_filters(stmt: Select, model, filters: dict[str, Any]) -> Select:
    """
    Dynamically apply equality filters to a SQLAlchemy select statement.

    Args:
        stmt: The base SQLAlchemy select statement.
        model: The SQLAlchemy model class to filter on.
        filters: A dict of {column_name: value}. None values are ignored.
               List values use IN operator, single values use equality.

    Returns:
        The select statement with filters applied.

    Example:
        stmt = apply_filters(select(Observation), Observation, {"datastream_id": some_uuid})
        stmt = apply_filters(select(Datastream), Datastream, {"system_id": some_uuid})
        stmt = apply_filters(select(Observation), Observation, {"datastream_id": [uuid1, uuid2]})
    """
    for field, value in filters.items():
        if value is not None:
            column = getattr(model, field, None)
            if column is not None:
                if isinstance(value, list):
                    stmt = stmt.where(column.in_(value))
                else:
                    stmt = stmt.where(column == value)
    return stmt


def _parse_single_timestamp(value: str) -> datetime:
    """Parse a single timestamp string — either 'now' or ISO format."""
    if value.strip().lower() == "now":
        return datetime.now(tz=timezone.utc)
    try:
        dt = datetime.fromisoformat(value.strip())
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid timestamp '{value}'. Use ISO format (e.g. 2026-02-28T17:01:05) or 'now'."
        )


def parse_time_param(time: str) -> tuple[datetime | str, datetime | None]:
    """
    Parse the time query parameter.

    Accepted formats:
        - "2026-02-28T17:01:05"        → time_start only
        - "now"                          → time_start = current UTC time
        - "latest"                       → time_start = "latest" (special marker)
        - "2026-02-28T17:01:05/now"     → time_start / time_end
        - "2026-02-28T17:01:05/2026-03-01T00:00:00" → time_start / time_end
        - "now/2026-03-01T00:00:00"     → time_start / time_end

    Returns:
        (time_start, time_end) — time_start can be "latest" (str), datetime, or None.
    """
    # Check if 'latest' is used - only allowed alone
    if time.strip().lower() == "latest":
        return "latest", None
    
    # Reject if 'latest' appears with /
    if "/" in time:
        parts = time.split("/")
        for part in parts:
            if part.strip().lower() == "latest":
                raise HTTPException(
                    status_code=422,
                    detail="'latest' can only be used alone, not combined with time ranges."
                )
        # Normal range parsing
        if len(parts) == 2:
            time_start = _parse_single_timestamp(parts[0])
            time_end = _parse_single_timestamp(parts[1])
            if time_start >= time_end:
                raise HTTPException(status_code=422, detail="time_start must be before time_end.")
            return time_start, time_end
        else:
            raise HTTPException(status_code=422, detail="Invalid time format. Use 'timestamp' or 'timestamp1/timestamp2'.")
    else:
        # Single timestamp
        return _parse_single_timestamp(time), None


def apply_time_range(stmt: Select, column, time_start: datetime, time_end: datetime | None) -> Select:
    """Apply a time range filter to a SQLAlchemy select statement."""
    stmt = stmt.where(column >= time_start)
    if time_end is not None:
        stmt = stmt.where(column <= time_end)
    return stmt


def filter_by_keywords(query: Select, model, q: Optional[str]) -> Select:
    """
    Filter by keyword search on name and description fields.

    Args:
        query: The base SQLAlchemy select statement.
        model: The SQLAlchemy model class to filter on.
        q: Comma-separated keywords. If None, returns query unchanged.
           Each keyword is matched against name and description (case-insensitive).

    Returns:
        The select statement with keyword filters applied using OR logic.

    Example:
        query = select(System)
        query = filter_by_keywords(query, System, "weather,outdoor")
    """
    if not q:
        return query

    keyword_filters = []
    keywords = [kw.strip() for kw in q.split(",") if kw.strip()]
    for kw in keywords:
        ilike_pattern = f"%{kw}%"
        keyword_filters.append(model.name.ilike(ilike_pattern))
        keyword_filters.append(model.description.ilike(ilike_pattern))

    return query.where(or_(*keyword_filters))
