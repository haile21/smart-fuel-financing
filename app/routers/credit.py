"""
Credit router: Credit line and risk scoring endpoints.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.credit_engine_service import CreditEngineService
from app.schemas.credit import CreditLineRead

router = APIRouter()


@router.post("/credit-lines", response_model=CreditLineRead)
def create_credit_line(
    bank_id: int,
    driver_id: int,
    credit_limit: float,
    request: Request = None,
    db: Session = Depends(get_db),
):
    trace_id = getattr(request.state, "trace_id", "")
    service = CreditEngineService(db)
    
    try:
        credit_line = service.create_credit_line(
            bank_id=bank_id,
            driver_id=driver_id,
            credit_limit=credit_limit,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return CreditLineRead(
        id=credit_line.id,
        bank_id=credit_line.bank_id,
        driver_id=credit_line.driver_id,
        credit_limit=float(credit_line.credit_limit),
        utilized_amount=float(credit_line.utilized_amount),
        version=credit_line.version,
    )


@router.get("/available-credit")
def get_available_credit(
    driver_id: int,
    request: Request = None,
    db: Session = Depends(get_db),
):
    trace_id = getattr(request.state, "trace_id", "")
    service = CreditEngineService(db)
    
    available = service.get_available_credit(driver_id=driver_id)
    
    return {"trace_id": trace_id, "available_credit": available}


@router.get("/check-availability")
def check_credit_availability(
    driver_id: int,
    requested_amount: float,
    request: Request = None,
    db: Session = Depends(get_db),
):
    trace_id = getattr(request.state, "trace_id", "")
    service = CreditEngineService(db)
    
    is_available, available = service.check_credit_availability(
        driver_id=driver_id,
        requested_amount=requested_amount,
    )
    
    return {
        "trace_id": trace_id,
        "is_available": is_available,
        "available_amount": available,
        "requested_amount": requested_amount,
    }

