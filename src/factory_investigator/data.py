"""Validated telemetry and interchangeable local/Snowflake readers."""
from __future__ import annotations

import csv
import math
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class Reading:
    timestamp: datetime
    asset_id: str
    speed: float
    load: float
    ambient: float
    temperature: float
    vibration: float
    pressure: float
    fault: str = "healthy"

    def __post_init__(self):
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("Telemetry timestamps must include a timezone")
        object.__setattr__(self, "timestamp", self.timestamp.astimezone(timezone.utc))
        if not self.asset_id.strip():
            raise ValueError("asset_id is required")
        for name in ("speed", "load", "ambient", "temperature", "vibration", "pressure"):
            if not math.isfinite(getattr(self, name)):
                raise ValueError(f"{name} must be finite")
        if self.speed < 0 or not 0 <= self.load <= 1:
            raise ValueError("speed must be nonnegative and load must be between 0 and 1")

    @classmethod
    def from_mapping(cls, row: dict) -> Reading:
        values = dict(row)
        if isinstance(values["timestamp"], str):
            values["timestamp"] = datetime.fromisoformat(values["timestamp"])
        for name in ("speed", "load", "ambient", "temperature", "vibration", "pressure"):
            values[name] = float(values[name])
        return cls(**values)


def validate_series(rows: list[Reading], minimum: int = 1) -> None:
    if len(rows) < minimum:
        raise ValueError(f"Need at least {minimum} readings")
    if len({r.asset_id for r in rows}) != 1:
        raise ValueError("A time series must contain exactly one asset")
    if any(a.timestamp >= b.timestamp for a, b in zip(rows, rows[1:])):
        raise ValueError("Readings must be strictly chronological without duplicates")


class TelemetrySource(Protocol):
    def read(self, asset_id: str, start: datetime, end: datetime) -> list[Reading]: ...


def validate_window(start: datetime, end: datetime) -> None:
    if start.utcoffset() is None or end.utcoffset() is None or start >= end:
        raise ValueError("Use timezone-aware start < end; windows are [start, end)")


class CSVSource:
    def __init__(self, path: Path):
        self.path = path

    def read(self, asset_id: str, start: datetime, end: datetime) -> list[Reading]:
        validate_window(start, end)
        with self.path.open(newline="") as stream:
            rows = [Reading.from_mapping(row) for row in csv.DictReader(stream)]
        selected = sorted((r for r in rows if r.asset_id == asset_id and start <= r.timestamp < end),
                          key=lambda r: r.timestamp)
        if selected:
            validate_series(selected)
        return selected


def write_csv(path: Path, rows: list[Reading]) -> None:
    validate_series(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(asdict(rows[0])))
        writer.writeheader()
        for row in rows:
            values = asdict(row)
            values["timestamp"] = row.timestamp.isoformat()
            writer.writerow(values)


class SnowflakeSource:
    """Accepts an existing connector connection. Never accepts arbitrary SQL."""
    def __init__(self, connection, table: str):
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*){0,2}", table):
            raise ValueError("Use an unquoted table, schema.table, or database.schema.table")
        self.connection = connection
        self.table = table

    def read(self, asset_id: str, start: datetime, end: datetime) -> list[Reading]:
        validate_window(start, end)
        # The connection must use the connector's default pyformat parameter style.
        sql = ("SELECT timestamp, asset_id, speed, load, ambient, temperature, vibration, pressure "
               f"FROM {self.table} WHERE asset_id = %s AND timestamp >= %s AND timestamp < %s "
               "ORDER BY timestamp")
        with self.connection.cursor() as cursor:
            cursor.execute(sql, (asset_id, start, end))
            names = [column[0].lower() for column in cursor.description]
            rows = [Reading.from_mapping(dict(zip(names, row))) for row in cursor.fetchall()]
        if rows:
            validate_series(rows)
        return rows
