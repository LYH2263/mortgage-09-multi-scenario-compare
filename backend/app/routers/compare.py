from fastapi import APIRouter, HTTPException
from app.schemas.compare import CompareRequest
from app.services.mortgage_service import MortgageService, CompareError
router = APIRouter()
@router.post("/compare")
def post_compare(body: CompareRequest):
    with MortgageService() as s:
        try:
            return s.compare(body.principal, body.plans, body.loan_id, body.persist)
        except CompareError as e:
            raise HTTPException(status_code=400, detail=str(e))
