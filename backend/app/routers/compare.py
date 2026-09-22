from fastapi import APIRouter, HTTPException
from app.schemas.schedule import CompareRequest
from app.services.mortgage_service import MortgageService, PlanValidationError
router = APIRouter()


@router.post("/compare")
def post_compare(body: CompareRequest):
    with MortgageService() as s:
        try:
            return s.compare(body.principal, body.plans, body.loan_id, body.persist)
        except PlanValidationError as e:
            # 某套非法 → 整单失败，写明套号
            raise HTTPException(status_code=422, detail=str(e))
