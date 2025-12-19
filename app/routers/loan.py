"""
Loan router: Loan management and repayment endpoints.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.loan_service import LoanService
from app.schemas.loan import (
    LoanResponse,
    RepaymentRequest,
    RepaymentResponse,
    LoanStatementResponse,
)

router = APIRouter()


@router.get("/loans", response_model=list[LoanResponse])
def get_loans(
    driver_id: int = None,
    agency_id: int = None,
    status: str = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    trace_id = getattr(request.state, "trace_id", "")
    service = LoanService(db)
    
    loans = service.get_loans(driver_id=driver_id, agency_id=agency_id, status=status)
    
    return [
        LoanResponse(
            id=loan.id,
            principal_amount=float(loan.principal_amount),
            outstanding_balance=float(loan.outstanding_balance),
            interest_rate=float(loan.interest_rate),
            status=loan.status,
            due_date=loan.due_date.isoformat() if loan.due_date else None,
            created_at=loan.created_at.isoformat(),
        )
        for loan in loans
    ]


@router.get("/loans/{loan_id}/statement", response_model=LoanStatementResponse)
def get_loan_statement(
    loan_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    trace_id = getattr(request.state, "trace_id", "")
    service = LoanService(db)
    
    try:
        statement = service.get_loan_statement(loan_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    return LoanStatementResponse(**statement)


@router.post("/loans/{loan_id}/repay", response_model=RepaymentResponse)
def record_repayment(
    loan_id: int,
    payload: RepaymentRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    trace_id = getattr(request.state, "trace_id", "")
    service = LoanService(db)
    
    try:
        repayment = service.record_repayment(
            loan_id=loan_id,
            amount=payload.amount,
            payment_method=payload.payment_method,
            payment_reference=payload.payment_reference,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return RepaymentResponse(
        id=repayment.id,
        amount=float(repayment.amount),
        payment_method=repayment.payment_method,
        repaid_at=repayment.repaid_at.isoformat(),
    )

