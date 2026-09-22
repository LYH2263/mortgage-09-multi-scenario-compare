import math

from app.db import connect
from app.engines.amortization import equal_payment_schedule
from app.repositories import loans, runs, settings


class PlanValidationError(ValueError):
    """某一套方案输入非法；整单失败，错误信息须写明套号。"""

    def __init__(self, index: int, reason: str):
        self.index = index
        super().__init__(f"第{index}套方案非法：{reason}")


class MortgageService:
    def __init__(self): self._c = connect()
    def close(self): self._c.close()
    def __enter__(self): return self
    def __exit__(self, *a): self.close()
    def list_loans(self): return loans.list_all(self._c)
    def loan(self, lid): return loans.get(self._c, lid)
    def settings(self): return settings.get_map(self._c)
    def history(self, limit=50): return runs.list_recent(self._c, limit)
    def schedule(self, principal, annual_rate, months, loan_id, persist, preview_rows=12):
        full = equal_payment_schedule(principal, annual_rate, months)
        out = {k: full[k] for k in ("monthly_payment", "total_interest", "total_payment")}
        out["preview"] = full["rows"][:preview_rows]
        out["row_count"] = len(full["rows"])
        rid = None
        if persist:
            rid = runs.insert(self._c, "schedule", {"principal": principal, "annual_rate": annual_rate, "months": months}, out, loan_id)
        return {"run_id": rid, **out}

    def compare(self, principal, plans, loan_id=None, persist=True):
        results = []
        for i, p in enumerate(plans, start=1):
            rate = p.annual_rate
            months = p.months
            if not isinstance(rate, (int, float)) or isinstance(rate, bool) or not math.isfinite(rate) or rate < 0:
                raise PlanValidationError(i, f"年利率须为非负有限数（收到 {rate!r}）")
            if not isinstance(months, int) or isinstance(months, bool) or not (0 < months <= 600):
                raise PlanValidationError(i, f"期数须为 1~600 的整数（收到 {months!r}）")
            full = equal_payment_schedule(principal, rate, months)
            results.append({
                "plan_index": i,
                "annual_rate": rate,
                "months": months,
                "monthly_payment": full["monthly_payment"],
                "total_interest": full["total_interest"],
                "total_payment": full["total_payment"],
            })
        # 利息升序，并列时套号小者靠前
        order = sorted(range(len(results)), key=lambda k: (results[k]["total_interest"], k))
        best_pos, second_pos = order[0], order[1]
        out = {
            "principal": principal,
            "plans": results,
            "best_index": best_pos + 1,
            "runner_up_index": second_pos + 1,
            "interest_gap": round(results[second_pos]["total_interest"] - results[best_pos]["total_interest"], 2),
        }
        rid = None
        if persist:
            # 只落一条对照记录，钉住各套输入与结果，禁止拆成多条
            rid = runs.insert(
                self._c, "compare",
                {"principal": principal, "plans": [{"annual_rate": p.annual_rate, "months": p.months} for p in plans]},
                out, loan_id,
            )
        return {"run_id": rid, **out}

    def dashboard(self):
        items = loans.list_all(self._c)
        return {"loan_count": len(items), "clean": len([x for x in items if "种子" not in x["name"]]), "dirty": len([x for x in items if "种子" in x["name"]])}
