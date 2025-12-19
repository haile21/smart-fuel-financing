"""
Loan Management Service: Handles loan lifecycle, repayment tracking, and statements.
"""

from datetime import datetime, timedelta
from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.entities import (
    Loan,
    LoanRepayment,
    LoanStatus,
    CreditLine,
    Transaction,
)


class LoanService:
    """
    Loan management service for tracking debts and repayments.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_loan_from_transaction(
        self,
        transaction_id: int,
        credit_line_id: int,
    ) -> Loan:
        """
        Create a loan record from a settled transaction.
        """
        transaction = self.db.get(Transaction, transaction_id)
        if not transaction or not transaction.settled_amount:
            raise ValueError("Transaction not found or not settled")
        
        credit_line = self.db.get(CreditLine, credit_line_id)
        if not credit_line:
            raise ValueError("Credit line not found")
        
        # Check if loan already exists for this transaction
        existing = (
            self.db.query(Loan)
            .filter(Loan.credit_line_id == credit_line_id)
            .filter(Loan.status == LoanStatus.ACTIVE.value)
            .first()
        )
        
        if existing:
            # Add to existing loan
            existing.principal_amount += transaction.settled_amount
            existing.outstanding_balance += transaction.settled_amount
            self.db.commit()
            self.db.refresh(existing)
            return existing
        
        # Create new loan
        loan = Loan(
            credit_line_id=credit_line_id,
            driver_id=transaction.debtor_driver_id,
            agency_id=transaction.debtor_agency_id,
            principal_amount=transaction.settled_amount,
            outstanding_balance=transaction.settled_amount,
            interest_rate=0.0,  # Can be configured per credit line
            status=LoanStatus.ACTIVE.value,
            due_date=datetime.utcnow() + timedelta(days=30),  # Default 30 days
        )
        self.db.add(loan)
        self.db.commit()
        self.db.refresh(loan)
        return loan

    def record_repayment(
        self,
        loan_id: int,
        amount: float,
        payment_method: str,
        payment_reference: Optional[str] = None,
    ) -> LoanRepayment:
        """
        Record a repayment against a loan.
        """
        loan = self.db.get(Loan, loan_id)
        if not loan:
            raise ValueError("Loan not found")
        
        if loan.outstanding_balance < amount:
            raise ValueError("Repayment amount exceeds outstanding balance")
        
        repayment = LoanRepayment(
            loan_id=loan_id,
            amount=amount,
            payment_method=payment_method,
            payment_reference=payment_reference,
        )
        self.db.add(repayment)
        
        # Update loan balance
        loan.outstanding_balance -= amount
        
        # Update credit line utilized amount
        credit_line = self.db.get(CreditLine, loan.credit_line_id)
        if credit_line:
            credit_line.utilized_amount = max(0.0, credit_line.utilized_amount - amount)
        
        # Check if loan is paid off
        if loan.outstanding_balance <= 0:
            loan.status = LoanStatus.PAID_OFF.value
            loan.paid_off_at = datetime.utcnow()
        
        # Check if overdue
        if loan.due_date and loan.due_date < datetime.utcnow() and loan.outstanding_balance > 0:
            loan.status = LoanStatus.OVERDUE.value
        
        self.db.commit()
        self.db.refresh(repayment)
        return repayment

    def get_loans(
        self,
        *,
        driver_id: Optional[int] = None,
        agency_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[Loan]:
        """
        Get loans for a driver or agency, optionally filtered by status.
        """
        query = self.db.query(Loan)
        
        if driver_id:
            query = query.filter(Loan.driver_id == driver_id)
        elif agency_id:
            query = query.filter(Loan.agency_id == agency_id)
        
        if status:
            query = query.filter(Loan.status == status)
        
        return query.order_by(Loan.created_at.desc()).all()

    def get_loan_statement(
        self,
        loan_id: int,
    ) -> dict:
        """
        Get detailed statement for a loan including all repayments.
        """
        loan = self.db.get(Loan, loan_id)
        if not loan:
            raise ValueError("Loan not found")
        
        repayments = (
            self.db.query(LoanRepayment)
            .filter(LoanRepayment.loan_id == loan_id)
            .order_by(LoanRepayment.repaid_at)
            .all()
        )
        
        return {
            "loan_id": loan.id,
            "principal_amount": float(loan.principal_amount),
            "outstanding_balance": float(loan.outstanding_balance),
            "interest_rate": float(loan.interest_rate),
            "status": loan.status,
            "due_date": loan.due_date.isoformat() if loan.due_date else None,
            "created_at": loan.created_at.isoformat(),
            "paid_off_at": loan.paid_off_at.isoformat() if loan.paid_off_at else None,
            "total_repaid": float(loan.principal_amount - loan.outstanding_balance),
            "repayments": [
                {
                    "id": r.id,
                    "amount": float(r.amount),
                    "payment_method": r.payment_method,
                    "payment_reference": r.payment_reference,
                    "repaid_at": r.repaid_at.isoformat(),
                }
                for r in repayments
            ],
        }

    def update_loan_due_date(
        self,
        loan_id: int,
        due_date: datetime,
    ) -> Loan:
        """
        Update loan due date (e.g., for extensions).
        """
        loan = self.db.get(Loan, loan_id)
        if not loan:
            raise ValueError("Loan not found")
        
        loan.due_date = due_date
        
        # Recheck overdue status
        if loan.due_date < datetime.utcnow() and loan.outstanding_balance > 0:
            loan.status = LoanStatus.OVERDUE.value
        
        self.db.commit()
        self.db.refresh(loan)
        return loan

