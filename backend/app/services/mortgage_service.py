from app.db import connect
from app.engines.amortization import equal_payment_schedule
from app.repositories import loans, runs, settings

class CompareError(ValueError):
    """某一套输入非法，message 已写明套号，整单失败。"""

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
    def dashboard(self):
        items = loans.list_all(self._c)
        return {"loan_count": len(items), "clean": len([x for x in items if "种子" not in x["name"]]), "dirty": len([x for x in items if "种子" in x["name"]])}

    def compare(self, principal, plans, loan_id=None, persist=True):
        # 各套单独校验：任一套非法则整单失败，错误写明套号（从 1 起）
        results = []
        for idx, p in enumerate(plans, start=1):
            if p.annual_rate < 0:
                raise CompareError(f"第{idx}套年利率不能为负")
            if p.months <= 0:
                raise CompareError(f"第{idx}套期数必须为正整数")
            if p.months > 600:
                raise CompareError(f"第{idx}套期数不能超过600个月")
            full = equal_payment_schedule(principal, p.annual_rate, p.months)
            results.append({
                "index": idx,
                "annual_rate": p.annual_rate,
                "months": p.months,
                "monthly_payment": full["monthly_payment"],
                "total_interest": full["total_interest"],
                "total_payment": full["total_payment"],
            })
        order = sorted(results, key=lambda x: x["total_interest"])
        best = order[0]["index"]
        runner = order[1]["index"]
        interest_gap = round(order[1]["total_interest"] - order[0]["total_interest"], 2)
        # 落库只生成一条对照记录，钉住各套输入与结果，不拆成多条
        rid = None
        if persist:
            rid = runs.insert(self._c, "compare",
                {"principal": principal, "plans": [{"annual_rate": p.annual_rate, "months": p.months} for p in plans]},
                {"plans": results, "best_index": best, "runner_up_index": runner, "interest_gap": interest_gap},
                loan_id)
        return {"run_id": rid, "principal": principal, "plans": results,
                "best_index": best, "runner_up_index": runner, "interest_gap": interest_gap}
