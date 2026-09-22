import json

import pytest

from app.engines.amortization import equal_payment_schedule
from app.services.mortgage_service import MortgageService, PlanValidationError


def test_monthly_payment():
    s = equal_payment_schedule(1_000_000, 3.5, 360)
    assert s["monthly_payment"] == 4490.45


def test_first_period_interest():
    s = equal_payment_schedule(1_000_000, 3.5, 360)
    assert s["rows"][0]["interest"] == 2916.67
    assert s["rows"][0]["period"] == 1


def test_zero_rate():
    s = equal_payment_schedule(120000, 0, 12)
    assert s["monthly_payment"] == 10000.0


def test_bad_months():
    with pytest.raises(ValueError):
        equal_payment_schedule(100, 3, 0)


class _Plan:
    def __init__(self, annual_rate, months):
        self.annual_rate = annual_rate
        self.months = months


@pytest.fixture
def service(tmp_path, monkeypatch):
    import app.db as db
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "compare.db")
    conn = db.connect()
    conn.execute(
        "CREATE TABLE calc_runs(id INTEGER PRIMARY KEY, kind TEXT, loan_id INTEGER,"
        " input_json TEXT, result_json TEXT, created_at TEXT)"
    )
    conn.commit()
    conn.close()
    with MortgageService() as s:
        yield s
    # 每个用例独立库，杜绝跨用例/后续对照改写历史快照


def test_compare_picks_lowest_interest_and_gap(service):
    plans = [_Plan(3.5, 360), _Plan(4.2, 300), _Plan(3.0, 240)]
    out = service.compare(1_000_000, plans, persist=False)
    interests = [equal_payment_schedule(1_000_000, p.annual_rate, p.months)["total_interest"] for p in plans]
    assert [p["plan_index"] for p in out["plans"]] == [1, 2, 3]
    assert out["best_index"] == interests.index(min(interests)) + 1
    ordered = sorted(interests)
    assert out["interest_gap"] == round(ordered[1] - ordered[0], 2)
    assert out["run_id"] is None
    for p, src in zip(out["plans"], plans):
        assert p["annual_rate"] == src.annual_rate and p["months"] == src.months
        assert "monthly_payment" in p and "total_payment" in p


def test_compare_tie_prefers_lower_index(service):
    out = service.compare(800_000, [_Plan(3.5, 360), _Plan(3.5, 360)], persist=False)
    assert out["best_index"] == 1
    assert out["runner_up_index"] == 2
    assert out["interest_gap"] == 0


def test_compare_invalid_plan_fails_whole_order(service):
    with pytest.raises(PlanValidationError) as ei:
        service.compare(1_000_000, [_Plan(3.5, 360), _Plan(4.2, 0)], persist=False)
    assert ei.value.index == 2
    assert "第2套" in str(ei.value)

    with pytest.raises(PlanValidationError) as ei:
        service.compare(1_000_000, [_Plan(3.5, 360), _Plan(4.2, 240), _Plan(-1.0, 120)], persist=False)
    assert ei.value.index == 3
    assert "第3套" in str(ei.value)

    with pytest.raises(PlanValidationError):
        service.compare(1_000_000, [_Plan(3.5, 360), _Plan(4.2, 601)], persist=False)
    # 整单失败：不落任何记录
    assert service.history() == []


def test_compare_persists_single_snapshot_row(service):
    plans = [_Plan(3.5, 360), _Plan(4.2, 300), _Plan(3.0, 240)]
    out = service.compare(1_000_000, plans, persist=True)
    rows = service.history()
    assert len(rows) == 1  # 禁止拆成多条
    row = rows[0]
    assert row["kind"] == "compare"
    assert out["run_id"] == row["id"]
    saved_in = json.loads(row["input_json"])
    saved_out = json.loads(row["result_json"])
    assert saved_in["principal"] == 1_000_000
    assert len(saved_in["plans"]) == 3
    assert [p["months"] for p in saved_in["plans"]] == [360, 300, 240]
    assert saved_out["best_index"] == out["best_index"]
    assert [p["plan_index"] for p in saved_out["plans"]] == [1, 2, 3]

    # 再来一次新对照：旧记录快照不被改写
    service.compare(500_000, [_Plan(2.9, 120), _Plan(3.1, 240)], persist=True)
    rows = service.history()
    assert len(rows) == 2
    old = next(r for r in rows if r["id"] == row["id"])
    assert json.loads(old["input_json"]) == saved_in
    assert json.loads(old["result_json"]) == saved_out
