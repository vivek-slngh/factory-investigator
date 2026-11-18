"""Linear sensor surrogate with separate temporal residual calibration."""
from __future__ import annotations
from dataclasses import dataclass

import numpy as np

from .data import Reading, validate_series

SENSORS = ("temperature", "vibration", "pressure")


def features(rows):
    return np.array([[1, r.speed / 1800, r.load, r.ambient / 30] for r in rows])


def targets(rows):
    return np.array([[getattr(r, s) for s in SENSORS] for r in rows])


@dataclass
class Twin:
    asset_id: str
    coefficients: np.ndarray
    scale: np.ndarray
    threshold: float
    trained_until: object
    speed_range: tuple[float, float]
    load_range: tuple[float, float]
    ambient_range: tuple[float, float]

    @classmethod
    def fit(cls, train: list[Reading], calibration: list[Reading]) -> Twin:
        validate_series(train, 30)
        validate_series(calibration, 30)
        if train[0].asset_id != calibration[0].asset_id:
            raise ValueError("Training and calibration assets must match")
        if train[-1].timestamp >= calibration[0].timestamp:
            raise ValueError("Calibration must follow training without overlap")
        x = features(train)
        if np.linalg.matrix_rank(x) < x.shape[1]:
            raise ValueError("Training operating conditions do not identify the model")
        coefficients = np.linalg.lstsq(x, targets(train), rcond=None)[0]
        residuals = targets(train) - x @ coefficients
        scale = np.maximum(np.std(residuals, axis=0, ddof=x.shape[1]), 1e-6)
        scores = np.max(np.abs(targets(calibration) - features(calibration) @ coefficients) / scale, axis=1)
        threshold = max(3.0, float(np.quantile(scores, 0.99, method="higher")))
        return cls(train[0].asset_id, coefficients, scale, threshold, calibration[-1].timestamp,
                   (min(r.speed for r in train), max(r.speed for r in train)),
                   (min(r.load for r in train), max(r.load for r in train)),
                   (min(r.ambient for r in train), max(r.ambient for r in train)))

    def score(self, rows: list[Reading]) -> list[dict]:
        validate_series(rows)
        if rows[0].asset_id != self.asset_id:
            raise ValueError("Twin belongs to a different asset")
        if rows[0].timestamp <= self.trained_until:
            raise ValueError("Evaluation must follow training and calibration")
        expected = features(rows) @ self.coefficients
        z = (targets(rows) - expected) / self.scale
        results = []
        for row, prediction, residual in zip(rows, expected, z):
            score = float(np.max(np.abs(residual)))
            out_of_range = any(not bounds[0] <= value <= bounds[1] for value, bounds in
                               ((row.speed, self.speed_range), (row.load, self.load_range),
                                (row.ambient, self.ambient_range)))
            results.append({"timestamp": row.timestamp.isoformat(), "asset_id": row.asset_id,
                            "score": score, "anomaly": score > self.threshold,
                            "outside_training_range": out_of_range,
                            "expected": dict(zip(SENSORS, map(float, prediction))),
                            "observed": {s: getattr(row, s) for s in SENSORS},
                            "residual_z": dict(zip(SENSORS, map(float, residual)))})
        return results
