"""Seeded synthetic pump scenarios; labels are evaluation-only metadata."""
from datetime import datetime, timedelta, timezone

import numpy as np

from .data import Reading


def generate(seed: int = 42, count: int = 720) -> list[Reading]:
    if count < 200:
        raise ValueError("Generate at least 200 samples for chronological splits")
    rng = np.random.default_rng(seed)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
    for i in range(count):
        speed = float(rng.uniform(900, 1800))
        load = float(rng.uniform(0.2, 0.95))
        ambient = float(rng.uniform(18, 32))
        temperature = 20 + 0.012 * speed + 18 * load + 0.6 * ambient + rng.normal(0, 0.4)
        vibration = 0.2 + 0.0006 * speed + 0.8 * load + rng.normal(0, 0.035)
        pressure = 0.5 + 0.003 * speed + 1.2 * load + rng.normal(0, 0.06)
        fault = "healthy"
        if i >= int(count * 0.8):
            fault = "bearing_wear"
            temperature += 7
            vibration += 0.9
        rows.append(Reading(start + timedelta(minutes=i), "pump-01", speed, load,
                            ambient, float(temperature), float(vibration), float(pressure), fault))
    return rows
