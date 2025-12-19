"""
Reports API endpoints.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional

from app.db.session import get_db
from app.models.entities import Transaction, Loan, CreditLine, Driver, Agency

router = APIRouter()


@router.get("/reports/summary")
def get_summary_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    bank_id: Optional[int] = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    GET /reports/summary?start_date=2024-01-01&end_date=2024-01-31&bank_id=1
    Get summary report with key metrics.
    """
    trace_id = getattr(request.state, "trace_id", "")
    
    # Parse dates
    if start_date:
        start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    else:
        start = datetime.utcnow() - timedelta(days=30)
    
    if end_date:
        end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    else:
        end = datetime.utcnow()
    
    # Get transactions
    query = db.query(Transaction).filter(
        Transaction.authorized_at >= start,
        Transaction.authorized_at <= end,
    )
    
    if bank_id:
        query = query.filter(Transaction.funding_source_id == bank_id)
    
    transactions = query.all()
    
    # Calculate metrics
    total_transactions = len(transactions)
    total_volume = sum(float(t.settled_amount or t.authorized_amount) for t in transactions)
    settled_transactions = [t for t in transactions if t.status == "SETTLED"]
    total_settled = len(settled_transactions)
    total_settled_volume = sum(float(t.settled_amount) for t in settled_transactions if t.settled_amount)
    
    # Get loans
    loan_query = db.query(Loan)
    if bank_id:
        credit_lines = db.query(CreditLine).filter(CreditLine.bank_id == bank_id).all()
        credit_line_ids = [cl.id for cl in credit_lines]
        loan_query = loan_query.filter(Loan.credit_line_id.in_(credit_line_ids))
    
    loans = loan_query.all()
    total_loans = len(loans)
    active_loans = len([l for l in loans if l.status == "ACTIVE"])
    total_outstanding = sum(float(l.outstanding_balance) for l in loans)
    
    # Get drivers
    driver_count = db.query(Driver).count()
    
    return {
        "trace_id": trace_id,
        "period": {
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        },
        "transactions": {
            "total": total_transactions,
            "settled": total_settled,
            "total_volume": total_volume,
            "settled_volume": total_settled_volume,
        },
        "loans": {
            "total": total_loans,
            "active": active_loans,
            "total_outstanding": total_outstanding,
        },
        "drivers": {
            "total": driver_count,
        },
    }

