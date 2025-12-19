"""
Payment router: Payment processing and reconciliation endpoints.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.payment_service import PaymentService
from app.schemas.payment import (
    InitiatePaymentRequest,
    PaymentResponse,
)

router = APIRouter()


@router.post("/initiate", response_model=PaymentResponse)
def initiate_payment(
    payload: InitiatePaymentRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    trace_id = getattr(request.state, "trace_id", "")
    service = PaymentService(db)
    
    try:
        payment = service.initiate_payment(
            loan_id=payload.loan_id,
            transaction_id=payload.transaction_id,
            payer_id=payload.payer_id,
            payer_type=payload.payer_type,
            amount=payload.amount,
            payment_method=payload.payment_method,
            payment_reference=payload.payment_reference,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return PaymentResponse(
        id=payment.id,
        amount=float(payment.amount),
        currency=payment.currency,
        payment_method=payment.payment_method,
        status=payment.status,
        external_payment_id=payment.external_payment_id,
        created_at=payment.created_at.isoformat(),
    )


@router.get("/history", response_model=list[PaymentResponse])
def get_payment_history(
    payer_id: int = None,
    payer_type: str = None,
    loan_id: int = None,
    status: str = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    trace_id = getattr(request.state, "trace_id", "")
    service = PaymentService(db)
    
    payments = service.get_payment_history(
        payer_id=payer_id,
        payer_type=payer_type,
        loan_id=loan_id,
        status=status,
    )
    
    return [
        PaymentResponse(
            id=p.id,
            amount=float(p.amount),
            currency=p.currency,
            payment_method=p.payment_method,
            status=p.status,
            external_payment_id=p.external_payment_id,
            created_at=p.created_at.isoformat(),
        )
        for p in payments
    ]


@router.post("/webhook/reconcile")
def reconcile_payment_webhook(
    external_payment_id: str,
    amount: float,
    status: str,
    request: Request,
    db: Session = Depends(get_db),
):
    trace_id = getattr(request.state, "trace_id", "")
    service = PaymentService(db)
    
    payment = service.reconcile_payment(
        external_payment_id=external_payment_id,
        amount=amount,
        status=status,
    )
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )
    
    return {"trace_id": trace_id, "status": "success", "payment_status": payment.status}

