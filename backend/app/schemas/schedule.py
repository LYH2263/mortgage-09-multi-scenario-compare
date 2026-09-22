from pydantic import BaseModel, Field


class ScheduleRequest(BaseModel):
    principal: float = Field(gt=0)
    annual_rate: float = Field(ge=0)
    months: int = Field(gt=0, le=600)
    loan_id: int | None = None
    persist: bool = True
    preview_rows: int = Field(default=12, ge=1, le=120)


class ComparePlan(BaseModel):
    # 约束放在 service 逐套校验，错误信息须写明 1 基套号
    annual_rate: float
    months: int


class CompareRequest(BaseModel):
    principal: float = Field(gt=0)
    plans: list[ComparePlan] = Field(min_length=2, max_length=3)
    loan_id: int | None = None
    persist: bool = True
