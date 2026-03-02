from sqlalchemy import Select
from typing import Any


def apply_filters(stmt: Select, model, filters: dict[str, Any]) -> Select:
    """
    Dynamically apply equality filters to a SQLAlchemy select statement.

    Args:
        stmt: The base SQLAlchemy select statement.
        model: The SQLAlchemy model class to filter on.
        filters: A dict of {column_name: value}. None values are ignored.

    Returns:
        The select statement with filters applied.

    Example:
        stmt = apply_filters(select(Observation), Observation, {"datastream_id": some_uuid})
        stmt = apply_filters(select(Datastream), Datastream, {"system_id": some_uuid})
    """
    for field, value in filters.items():
        if value is not None:
            column = getattr(model, field, None)
            if column is not None:
                stmt = stmt.where(column == value)
    return stmt
