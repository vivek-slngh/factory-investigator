from dataclasses import replace
from datetime import timedelta
import json

import numpy as np
import pytest

from factory_investigator.data import CSVSource, Reading, SnowflakeSource, write_csv
from factory_investigator.demo import run_demo
from factory_investigator.investigation import investigate
from factory_investigator.retrieval import Retriever
from factory_investigator.simulation import generate
from factory_investigator.twin import Twin


@pytest.fixture
def rows():
    return generate()


def test_demo_artifacts_and_detection(tmp_path):
    report = run_demo(tmp_path)
    assert report['experiment']['fault_recall'] >= 0.95
    assert report['experiment']['false_positive_rate'] <= 0.05
    assert 'Bearing wear' in report['hypothesis']
    assert report['evidence']
    assert json.loads((tmp_path / 'report.json').read_text()) == report
    assert len(json.loads((tmp_path / 'scores.json').read_text())) == 216
    assert report['evidence'][0]['citation'] in (tmp_path / 'report.md').read_text()


def test_reproducible():
    assert generate(17) == generate(17)
    assert generate(17) != generate(18)


@pytest.mark.parametrize('seed', [1, 8, 21])
def test_detection_generalizes_to_other_seeds(seed):
    rows = generate(seed)
    twin = Twin.fit(rows[:360], rows[360:504])
    scored = twin.score(rows[504:])
    assert sum(s['anomaly'] for s in scored[:72]) / 72 <= 0.1
    assert sum(s['anomaly'] for s in scored[72:]) / 144 >= 0.95


def test_labels_are_not_model_inputs(rows):
    changed = [replace(r, fault='unavailable') for r in rows]
    a = Twin.fit(rows[:360], rows[360:504])
    b = Twin.fit(changed[:360], changed[360:504])
    np.testing.assert_array_equal(a.coefficients, b.coefficients)
    assert a.score(rows[504:]) == b.score(changed[504:])


def test_temporal_leakage_is_rejected(rows):
    with pytest.raises(ValueError, match='Calibration must follow'):
        Twin.fit(rows[:360], rows[300:504])
    twin = Twin.fit(rows[:360], rows[360:504])
    with pytest.raises(ValueError, match='Evaluation must follow'):
        twin.score(rows[400:])


def test_invalid_data(rows):
    with pytest.raises(ValueError, match='finite'):
        replace(rows[0], vibration=float('nan'))
    with pytest.raises(ValueError, match='timezone'):
        replace(rows[0], timestamp=rows[0].timestamp.replace(tzinfo=None))
    with pytest.raises(ValueError, match='chronological'):
        Twin.fit([rows[0]] * 40, rows[360:504])
    with pytest.raises(ValueError, match='exactly one asset'):
        Twin.fit([replace(rows[0], asset_id='other')] + rows[1:360], rows[360:504])


def test_rank_deficient_training_rejected(rows):
    constant = [replace(r, speed=1000, load=0.5, ambient=20) for r in rows[:360]]
    with pytest.raises(ValueError, match='identify'):
        Twin.fit(constant, rows[360:504])


def test_csv_window_roundtrip(tmp_path, rows):
    path = tmp_path / 'data.csv'
    write_csv(path, rows)
    assert CSVSource(path).read('pump-01', rows[10].timestamp, rows[20].timestamp) == rows[10:20]
    assert CSVSource(path).read('unknown', rows[10].timestamp, rows[20].timestamp) == []


def test_retrieval_citations_and_empty_results():
    matches = Retriever().search('bearing lubrication vibration')
    assert any(m['citation'] == 'synthetic-pump-manual#bearing-inspection' for m in matches)
    assert all(m['text'] and m['source_id'] and m['section'] for m in matches)
    assert Retriever().search('xyznonexistent') == []
    assert Retriever([]).search('bearing') == []
    with pytest.raises(ValueError):
        Retriever().search('bearing', 100)


def test_healthy_investigation_does_not_invent_fault(rows):
    twin = Twin.fit(rows[:360], rows[360:504])
    healthy = [r for r in twin.score(rows[504:576]) if not r['anomaly']]
    report = investigate(healthy)
    assert report['hypothesis'] == 'No anomaly detected in this window.'
    assert report['evidence'] == []


def test_operating_envelope_warning(rows):
    twin = Twin.fit(rows[:360], rows[360:504])
    scored = twin.score([replace(rows[504], speed=3000)])
    assert scored[0]['outside_training_range']
    assert investigate(scored)['operating_conditions']['out_of_range_count'] == 1


def test_snowflake_parameterization_and_mapping(rows):
    class Cursor:
        description = [(name.upper(),) for name in
                       ('timestamp', 'asset_id', 'speed', 'load', 'ambient', 'temperature', 'vibration', 'pressure')]
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, sql, parameters): self.sql, self.parameters = sql, parameters
        def fetchall(self):
            r = rows[0]
            return [(r.timestamp, r.asset_id, r.speed, r.load, r.ambient, r.temperature, r.vibration, r.pressure)]
    class Connection:
        def __init__(self): self.result = Cursor()
        def cursor(self): return self.result
    connection = Connection()
    source = SnowflakeSource(connection, 'FACTORY.PUBLIC.TELEMETRY')
    asset = "pump'; DROP TABLE telemetry; --"
    assert source.read(asset, rows[0].timestamp, rows[1].timestamp) == rows[:1]
    assert asset not in connection.result.sql
    assert connection.result.parameters[0] == asset
    with pytest.raises(ValueError, match='table'):
        SnowflakeSource(connection, 'telemetry; DROP TABLE x')


def test_invalid_window(rows, tmp_path):
    with pytest.raises(ValueError, match='start < end'):
        CSVSource(tmp_path / 'missing').read('pump', rows[1].timestamp, rows[0].timestamp)
