"""Seed determinism: two consecutive mini-seeds must produce identical data.

This is the D12 reproducibility guarantee — the entire demo, dataset and ML
evaluation are reproducible from a fixed seed (42).
"""
import hashlib

from seeds.generate import build


def _content_hash():
    """Aggregate hash of a handful of stable rows from a fresh seed."""
    from app.db import engine
    from sqlalchemy import text

    build(days_per_year=15, limit_students=40)
    rows = engine.connect().execute(text(
        "SELECT id, admission_no, name, uin_id, date_of_birth FROM student "
        "ORDER BY id")).all()
    bills = engine.connect().execute(text(
        "SELECT student_id, installment, total, paid, status FROM bill ORDER BY id")).all()
    att = engine.connect().execute(text(
        "SELECT enrollment_id, d, type FROM attendance ORDER BY id")).all()
    blob = json_dump(rows) + json_dump(bills) + json_dump(att)
    return hashlib.sha256(blob.encode()).hexdigest()


def json_dump(rows):
    import json
    return json.dumps(rows, default=str, sort_keys=True)


def test_seed_is_reproducible():
    h1 = _content_hash()
    h2 = _content_hash()
    assert h1 == h2, "seed must be deterministic across runs"
