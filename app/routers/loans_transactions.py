"""
Loans & Transactions API endpoints.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.services.loan_service import LoanService
from app.schemas.loan import LoanStatementResponse

router = APIRouter()


class InitiateTransactionRequest(BaseModel):
    driver_id: int
    station_id: int
    authorized_amount: float
    idempotency_key: str


class CompleteTransactionRequest(BaseModel):
    transaction_id: int
    settled_amount: float


@router.get("/loans/{loan_id}")
def get_loan(
    loan_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    GET /loans/{loan_id}
    Get loan details and statement.
    """
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


@router.post("/transactions/initiate")
def initiate_transaction(
    payload: InitiateTransactionRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    POST /transactions/initiate
    Initiate a transaction (alternative to QR flow).
    """
    trace_id = getattr(request.state, "trace_id", "")
    from app.services.transaction_qr_service import TransactionQrService
    from app.models import Driver, FuelStation, CreditLine
    
    service = TransactionQrService(db)
    
    # Check credit availability
    driver = db.get(Driver, payload.driver_id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found",
        )
    
    station = db.get(FuelStation, payload.station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Station not found",
        )
    
    # Get credit line
    credit_line = (
        db.query(CreditLine)
        .filter(
            CreditLine.driver_id == driver.id,
            CreditLine.bank_id == driver.preferred_bank_id,
        )
        .first()
    )
    
    if not credit_line:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credit line not found",
        )
    
    # Create authorization transaction directly
    from app.models import Transaction
    
    transaction = Transaction(
        idempotency_key=payload.idempotency_key,
        funding_source_id=driver.preferred_bank_id,
        station_id=station.id,
        debtor_driver_id=driver.id,
        authorized_amount=payload.authorized_amount,
        settled_amount=None,
        status="AUTHORIZED",
    )
    db.add(transaction)
    
    # Update credit line
    credit_line.utilized_amount += payload.authorized_amount
    credit_line.version += 1
    
    db.commit()
    db.refresh(transaction)
    
    return {
        "trace_id": trace_id,
        "transaction_id": transaction.id,
        "status": transaction.status,
        "authorized_amount": float(transaction.authorized_amount),
        "authorized_at": transaction.authorized_at.isoformat(),
    }


@router.post("/transactions/complete")
def complete_transaction(
    payload: CompleteTransactionRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    POST /transactions/complete
    Complete a transaction (settle).
    """
    trace_id = getattr(request.state, "trace_id", "")
    service = TransactionQrService(db)
    
    try:
        transaction = service.settle_transaction(
            transaction_id=payload.transaction_id,
            settled_amount=payload.settled_amount,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    # Create loan from settled transaction
    if transaction.status == "SETTLED" and transaction.settled_amount:
        from app.services.loan_service import LoanService
        from app.models import CreditLine, Driver
        
        loan_service = LoanService(db)
        driver = db.get(Driver, transaction.debtor_driver_id)
        if driver:
            credit_line = (
                db.query(CreditLine)
                .filter(
                    CreditLine.driver_id == driver.id,
                    CreditLine.bank_id == transaction.funding_source_id,
                )
                .first()
            )
            if credit_line:
                try:
                    loan_service.create_loan_from_transaction(transaction.id, credit_line.id)
                except Exception:
                    pass
    
    return {
        "trace_id": trace_id,
        "transaction_id": transaction.id,
        "status": transaction.status,
        "settled_amount": float(transaction.settled_amount) if transaction.settled_amount else None,
        "settled_at": transaction.settled_at.isoformat() if transaction.settled_at else None,
    }

