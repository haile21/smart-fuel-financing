"""
Bank Integration API endpoints: eKYC verification, payment to station, auto-repayment.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.session import get_db
from app.services.kyc_service import KycService
from app.services.payment_service import PaymentService
from app.services.loan_service import LoanService

router = APIRouter()


class VerifyEkycRequest(BaseModel):
    driver_id: int
    document_id: int
    approved: bool
    rejection_reason: Optional[str] = None


class PayStationRequest(BaseModel):
    transaction_id: int
    amount: float
    payment_reference: Optional[str] = None


class AutoRepayRequest(BaseModel):
    loan_id: int
    amount: Optional[float] = None  # If None, pays full outstanding balance


@router.post("/bank/ekyc/verify")
def verify_ekyc(
    payload: VerifyEkycRequest,
    request: Request,
    reviewer_user_id: int = 1,  # In production, get from JWT token
    db: Session = Depends(get_db),
):
    """
    POST /bank/ekyc/verify
    Bank verifies eKYC documents.
    """
    trace_id = getattr(request.state, "trace_id", "")
    service = KycService(db)
    
    try:
        doc = service.verify_document(
            document_id=payload.document_id,
            verifier_user_id=reviewer_user_id,
            approved=payload.approved,
            rejection_reason=payload.rejection_reason,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    return {
        "trace_id": trace_id,
        "document_id": doc.id,
        "status": doc.status,
        "driver_id": payload.driver_id,
        "message": "eKYC verification completed",
    }


@router.post("/bank/pay-station")
def pay_station(
    payload: PayStationRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    POST /bank/pay-station
    Bank initiates payment to fuel station (merchant).
    This is called when station scans QR code.
    """
    trace_id = getattr(request.state, "trace_id", "")
    from app.models import Transaction, FuelStation
    
    transaction = db.get(Transaction, payload.transaction_id)
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
    
    if transaction.status != "AUTHORIZED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transaction is {transaction.status}, must be AUTHORIZED",
        )
    
    station = db.get(FuelStation, transaction.station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Station not found",
        )
    
    # In production, initiate bank transfer here:
    # Transfer amount from bank.account_number to station.bank_account_number
    
    # For now, just mark as ready for settlement
    return {
        "trace_id": trace_id,
        "transaction_id": transaction.id,
        "amount": payload.amount,
        "merchant_account": station.bank_account_number or "N/A",
        "status": "payment_initiated",
        "message": "Payment transfer initiated to merchant account",
    }


@router.post("/bank/auto-repay")
def auto_repay(
    payload: AutoRepayRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    POST /bank/auto-repay
    Bank automatically repays loan from driver's account or credit line.
    """
    trace_id = getattr(request.state, "trace_id", "")
    loan_service = LoanService(db)
    
    from app.models import Loan
    loan = db.get(Loan, payload.loan_id)
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan not found",
        )
    
    # Determine repayment amount
    amount = payload.amount if payload.amount else float(loan.outstanding_balance)
    
    if amount > loan.outstanding_balance:
        amount = float(loan.outstanding_balance)
    
    # Record repayment
    try:
        repayment = loan_service.record_repayment(
            loan_id=payload.loan_id,
            amount=amount,
            payment_method="AUTO_REPAY",
            payment_reference=f"auto-repay-{payload.loan_id}",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return {
        "trace_id": trace_id,
        "loan_id": payload.loan_id,
        "repayment_id": repayment.id,
        "amount": float(repayment.amount),
        "outstanding_balance": float(loan.outstanding_balance),
        "status": "completed",
        "message": "Auto-repayment completed successfully",
    }

