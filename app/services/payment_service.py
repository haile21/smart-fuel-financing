"""
Payment Service: Handles payment processing and reconciliation.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    Payment,
    PaymentStatus,
    Loan,
    Transaction,
)


class PaymentService:
    """
    Payment service for processing payments and reconciliation.
    """

    def __init__(self, db: Session):
        self.db = db

    def initiate_payment(
        self,
        *,
        loan_id: Optional[int] = None,
        transaction_id: Optional[int] = None,
        payer_id: int,
        payer_type: str,
        amount: float,
        payment_method: str,
        payment_reference: Optional[str] = None,
    ) -> Payment:
        """
        Initiate a payment (for loan repayment or other purposes).
        """
        if not loan_id and not transaction_id:
            raise ValueError("Either loan_id or transaction_id must be provided")
        
        payment = Payment(
            loan_id=loan_id,
            transaction_id=transaction_id,
            payer_id=payer_id,
            payer_type=payer_type,
            amount=amount,
            currency="ETB",
            payment_method=payment_method,
            payment_reference=payment_reference,
            status=PaymentStatus.PENDING.value,
        )
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        
        # Stub: In production, initiate payment with payment gateway
        # For now, auto-complete the payment
        return self.complete_payment(payment.id, external_payment_id=f"pay-{payment.id}")

    def complete_payment(
        self,
        payment_id: int,
        external_payment_id: str,
    ) -> Payment:
        """
        Mark payment as completed (called by payment gateway webhook or manually).
        """
        payment = self.db.get(Payment, payment_id)
        if not payment:
            raise ValueError("Payment not found")
        
        payment.status = PaymentStatus.COMPLETED.value
        payment.external_payment_id = external_payment_id
        payment.processed_at = datetime.utcnow()
        
        # If payment is for a loan, record repayment
        if payment.loan_id:
            from app.services.loan_service import LoanService
            loan_service = LoanService(self.db)
            loan_service.record_repayment(
                loan_id=payment.loan_id,
                amount=payment.amount,
                payment_method=payment.payment_method,
                payment_reference=payment.payment_reference,
            )
        
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def fail_payment(
        self,
        payment_id: int,
        failure_reason: str,
    ) -> Payment:
        """
        Mark payment as failed.
        """
        payment = self.db.get(Payment, payment_id)
        if not payment:
            raise ValueError("Payment not found")
        
        payment.status = PaymentStatus.FAILED.value
        # Store failure reason in payment_reference or add a new field
        
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def get_payment_history(
        self,
        *,
        payer_id: Optional[int] = None,
        payer_type: Optional[str] = None,
        loan_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> list[Payment]:
        """
        Get payment history with optional filters.
        """
        query = self.db.query(Payment)
        
        if payer_id:
            query = query.filter(Payment.payer_id == payer_id)
        if payer_type:
            query = query.filter(Payment.payer_type == payer_type)
        if loan_id:
            query = query.filter(Payment.loan_id == loan_id)
        if status:
            query = query.filter(Payment.status == status)
        
        return query.order_by(Payment.created_at.desc()).all()

    def reconcile_payment(
        self,
        external_payment_id: str,
        amount: float,
        status: str,
    ) -> Optional[Payment]:
        """
        Reconcile payment from external payment gateway webhook.
        """
        payment = (
            self.db.query(Payment)
            .filter(Payment.external_payment_id == external_payment_id)
            .first()
        )
        
        if not payment:
            # Payment not found - might be new from gateway
            return None
        
        if status == "COMPLETED":
            return self.complete_payment(payment.id, external_payment_id)
        elif status == "FAILED":
            return self.fail_payment(payment.id, "Payment gateway reported failure")
        
        return payment

