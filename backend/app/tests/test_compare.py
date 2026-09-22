import json
import os
import tempfile
from types import SimpleNamespace

import pytest

_tmp = tempfile.mkdtemp()
os.environ["DATA_DIR"] = _tmp

from app import seed  # noqa: E402
from app.db import connect  # noqa: E402
from app.engines.amortization import equal_payment_schedule  # noqa: E402
from app.services.mortgage_service import CompareError, MortgageService  # noqa: E402

seed.init_db()


def _plan(rate, months):
    return SimpleNamespace(annual_rate=rate, months=months)


def test_compare_two_plans_fields_and_best():
    with MortgageService() as s:
        out = s.compare(1_000_000, [_plan(3.5, 360), _plan(4.2, 360)], persist=False)
    assert out["run_id"] is None
    assert len(out["plans"]) == 2
    assert [p["index"] for p in out["plans"]] == [1, 2]
    e1 = equal_payment_schedule(1_000_000, 3.5, 360)
    e2 = equal_payment_schedule(1_000_000, 4.2, 360)
    assert out["plans"][0]["monthly_payment"] == e1["monthly_payment"]
    assert out["plans"][1]["total_interest"] == e2["total_interest"]
    assert out["plans"][0]["total_payment"] == e1["total_payment"]
    assert out["best_index"] == 1
    assert out["runner_up_index"] == 2
    assert out["interest_gap"] == round(e2["total_interest"] - e1["total_interest"], 2)
    assert out["interest_gap"] > 0


def test_compare_three_plans_zero_rate_is_best():
    with MortgageService() as s:
        out = s.compare(120_000, [_plan(6.0, 24), _plan(0, 12), _plan(3.5, 36)], persist=False)
    assert len(out["plans"]) == 3
    assert out["best_index"] == 2
    assert out["plans"][1]["total_interest"] == 0
    assert out["plans"][1]["monthly_payment"] == 10000.0
    # 最优与次小利差
    others = sorted(p["total_interest"] for p in out["plans"])
    assert out["interest_gap"] == round(others[1] - others[0], 2)


@pytest.mark.parametrize("bad_rate,bad_months,idx", [
    (3.0, 0, 1),
    (-1.0, 360, 2),
    (3.0, 601, 3),
])
def test_compare_invalid_plan_fails_whole_order(bad_rate, bad_months, idx):
    plans = [_plan(3.5, 360), _plan(3.5, 360), _plan(3.5, 360)]
    plans[idx - 1] = _plan(bad_rate, bad_months)
    c = connect()
    before = c.execute("SELECT COUNT(*) c FROM calc_runs WHERE kind='compare'").fetchone()["c"]
    c.close()
    with MortgageService() as s:
        with pytest.raises(CompareError) as exc:
            s.compare(800_000, plans, persist=True)
    assert f"第{idx}套" in str(exc.value)
    # 整单失败：不得留下任何对照落库
    c = connect()
    after = c.execute("SELECT COUNT(*) c FROM calc_runs WHERE kind='compare'").fetchone()["c"]
    assert after == before
    c.close()


def test_persist_writes_single_snapshot_row():
    c = connect()
    before = c.execute("SELECT COUNT(*) c FROM calc_runs WHERE kind='compare'").fetchone()["c"]
    with MortgageService() as s:
        out = s.compare(800_000, [_plan(3.5, 360), _plan(4.2, 240)], persist=True)
    rid = out["run_id"]
    assert rid is not None
    after = c.execute("SELECT COUNT(*) c FROM calc_runs WHERE kind='compare'").fetchone()["c"]
    assert after - before == 1  # 一次对照只落一条
    row = c.execute("SELECT * FROM calc_runs WHERE id=?", (rid,)).fetchone()
    payload = json.loads(row["input_json"])
    result = json.loads(row["result_json"])
    assert payload["principal"] == 800_000
    assert len(payload["plans"]) == 2  # 各套输入钉在同一条里
    assert len(result["plans"]) == 2  # 各套结果也钉在同一条里
    assert result["best_index"] == out["best_index"]
    # 后续新对照不得改写历史快照
    with MortgageService() as s:
        s.compare(500_000, [_plan(1.0, 12), _plan(2.0, 24)], persist=True)
    row_again = c.execute("SELECT * FROM calc_runs WHERE id=?", (rid,)).fetchone()
    assert row_again["input_json"] == row["input_json"]
    assert row_again["result_json"] == row["result_json"]
    c.close()
