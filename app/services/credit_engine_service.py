"""
Credit Engine Service: Handles risk scoring, credit limit calculation, and credit line management.
"""

from typing import Optional, Tuple
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.entities import (
    CreditLine,
    Driver,
    Bank,
    Transaction,
    Loan,
)


class CreditEngineService:
    """
    Credit engine for risk scoring and credit limit management.
    """

    def __init__(self, db: Session):
        self.db = db

    def calculate_driver_risk_score(
        self,
        driver: Driver,
    ) -> Tuple[str, float]:
        """
        Calculate risk category and credit limit for a driver.
        Returns (risk_category, credit_limit).
        """
        # Simple heuristic based on vehicle and consumption
        capacity = driver.fuel_tank_capacity_liters or 60.0
        consumption = driver.fuel_consumption_l_per_km or 0.12
        
        # Estimate monthly fuel consumption
        est_monthly_liters = capacity * 8  # ~8 fills per month
        
        if est_monthly_liters <= 400 and consumption <= 0.1:
            category = "LOW"
            limit = 5000.0
        elif est_monthly_liters >= 1000 or consumption >= 0.18:
            category = "HIGH"
            limit = 20000.0
        else:
            category = "MEDIUM"
            limit = 10000.0
        
        return category, limit

    def create_credit_line(
        self,
        *,
        bank_id: int,
        driver_id: int,
        credit_limit: float,
    ) -> CreditLine:
        """
        Create a new credit line for a driver.
        """
        # Check if credit line already exists
        existing = (
            self.db.query(CreditLine)
            .filter(
                CreditLine.bank_id == bank_id,
                CreditLine.driver_id == driver_id,
            )
            .first()
        )
        
        if existing:
            return existing
        
        credit_line = CreditLine(
            bank_id=bank_id,
            driver_id=driver_id,
            credit_limit=credit_limit,
            utilized_amount=0.0,
            version=0,
        )
        self.db.add(credit_line)
        self.db.commit()
        self.db.refresh(credit_line)
        return credit_line

    def get_available_credit(
        self,
        *,
        driver_id: int,
    ) -> float:
        """
        Get available credit for a driver.
        """
        driver = self.db.get(Driver, driver_id)
        if not driver:
            return 0.0
        
        # Driver's own credit line
        credit_line = (
            self.db.query(CreditLine)
            .filter(CreditLine.driver_id == driver_id)
            .first()
        )
        if credit_line:
            return max(0.0, credit_line.credit_limit - credit_line.utilized_amount)
        
        return 0.0

    def check_credit_availability(
        self,
        *,
        driver_id: int,
        requested_amount: float,
    ) -> Tuple[bool, float]:
        """
        Check if credit is available for a transaction.
        Returns (is_available, available_amount).
        """
        available = self.get_available_credit(driver_id=driver_id)
        return (available >= requested_amount, available)

