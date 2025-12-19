"""
Transaction router: Authorization, settlement, and QR code endpoints.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.transaction_qr_service import TransactionQrService
from app.services.loan_service import LoanService
from app.schemas.transaction_qr import (
    GenerateQrRequest,
    QrCodeResponse,
    ScanQrRequest,
    TransactionResponse,
    SettleTransactionRequest,
)

router = APIRouter()


@router.post("/qr/generate", response_model=QrCodeResponse)
def generate_qr_code(
    driver_id: int,
    payload: GenerateQrRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    trace_id = getattr(request.state, "trace_id", "")
    service = TransactionQrService(db)
    
    try:
        qr = service.generate_qr_code(
            driver_id=driver_id,
            station_id=payload.station_id,
            authorized_amount=payload.authorized_amount,
            expiry_minutes=payload.expiry_minutes,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return QrCodeResponse(
        id=qr.id,
        qr_data=qr.qr_data,
        qr_image_url=qr.qr_image_url,
        bank_account_number=qr.bank_account_number,
        amount=float(qr.amount),
        driver_phone_number=qr.driver_phone_number,
        bank_name=qr.bank_name,
        authorized_amount=float(qr.authorized_amount),
        expires_at=qr.expires_at.isoformat(),
    )


@router.post("/authorize", response_model=TransactionResponse)
def authorize_transaction(
    payload: ScanQrRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    trace_id = getattr(request.state, "trace_id", "")
    service = TransactionQrService(db)
    
    try:
        transaction = service.scan_and_authorize(
            qr_id=payload.qr_id,
            idempotency_key=payload.idempotency_key,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return TransactionResponse(
        id=transaction.id,
        idempotency_key=transaction.idempotency_key,
        authorized_amount=float(transaction.authorized_amount),
        settled_amount=float(transaction.settled_amount) if transaction.settled_amount else None,
        status=transaction.status,
        authorized_at=transaction.authorized_at.isoformat(),
        settled_at=transaction.settled_at.isoformat() if transaction.settled_at else None,
    )


@router.post("/{transaction_id}/settle", response_model=TransactionResponse)
def settle_transaction(
    transaction_id: int,
    payload: SettleTransactionRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    trace_id = getattr(request.state, "trace_id", "")
    service = TransactionQrService(db)
    
    try:
        transaction = service.settle_transaction(transaction_id, payload.settled_amount)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    # Create loan from settled transaction
    if transaction.status == "SETTLED" and transaction.settled_amount:
        loan_service = LoanService(db)
        # Find credit line for this transaction
        from app.models.entities import CreditLine, Driver
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
                    pass  # Log error but don't fail settlement
    
    return TransactionResponse(
        id=transaction.id,
        idempotency_key=transaction.idempotency_key,
        authorized_amount=float(transaction.authorized_amount),
        settled_amount=float(transaction.settled_amount) if transaction.settled_amount else None,
        status=transaction.status,
        authorized_at=transaction.authorized_at.isoformat(),
        settled_at=transaction.settled_at.isoformat() if transaction.settled_at else None,
    )

