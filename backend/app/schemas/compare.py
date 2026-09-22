from pydantic import BaseModel, Field

class ComparePlan(BaseModel):
    # 各套单独校验在 service 中完成，错误信息需写明套号
    annual_rate: float
    months: int

class CompareRequest(BaseModel):
    principal: float = Field(gt=0)
    plans: list[ComparePlan] = Field(min_length=2, max_length=3)
    loan_id: int | None = None
    persist: bool = True
