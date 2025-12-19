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
    Agency,
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

    def calculate_agency_risk_score(
        self,
        agency: Agency,
    ) -> float:
        """
        Calculate risk score for an agency based on:
        - Fleet size
        - Average repayment time
        - Monthly fuel consumption volume
        """
        fleet_size = agency.fleet_size or 1
        avg_repayment_days = agency.average_repayment_days or 30.0
        monthly_volume = agency.monthly_fuel_volume or 0.0
        
        # Normalize factors (simplified scoring)
        fleet_score = min(fleet_size / 50.0, 1.0) * 30  # Max 30 points
        repayment_score = max(0, (60 - avg_repayment_days) / 60.0) * 40  # Max 40 points (lower days = better)
        volume_score = min(monthly_volume / 100000.0, 1.0) * 30  # Max 30 points
        
        risk_score = fleet_score + repayment_score + volume_score
        
        # Convert to 0-100 scale
        return min(100.0, max(0.0, risk_score))

    def create_credit_line(
        self,
        *,
        bank_id: int,
        credit_limit: float,
        agency_id: Optional[int] = None,
        driver_id: Optional[int] = None,
    ) -> CreditLine:
        """
        Create a new credit line for a driver or agency.
        """
        if not agency_id and not driver_id:
            raise ValueError("Either agency_id or driver_id must be provided")
        
        # Check if credit line already exists
        existing = (
            self.db.query(CreditLine)
            .filter(
                CreditLine.bank_id == bank_id,
                CreditLine.agency_id == agency_id,
                CreditLine.driver_id == driver_id,
            )
            .first()
        )
        
        if existing:
            return existing
        
        credit_line = CreditLine(
            bank_id=bank_id,
            agency_id=agency_id,
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
        driver_id: Optional[int] = None,
        agency_id: Optional[int] = None,
    ) -> float:
        """
        Get available credit for a driver or agency.
        For drivers under an agency, checks agency's total available credit.
        """
        if driver_id:
            driver = self.db.get(Driver, driver_id)
            if not driver:
                return 0.0
            
            # If driver belongs to agency, check agency credit
            if driver.agency_id:
                agency_id = driver.agency_id
        
        if agency_id:
            # Sum all credit lines for this agency
            credit_lines = (
                self.db.query(CreditLine)
                .filter(CreditLine.agency_id == agency_id)
                .all()
            )
            total_limit = sum(cl.credit_limit for cl in credit_lines)
            total_utilized = sum(cl.utilized_amount for cl in credit_lines)
            return max(0.0, total_limit - total_utilized)
        
        if driver_id:
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
        driver_id: Optional[int] = None,
        agency_id: Optional[int] = None,
        requested_amount: float,
    ) -> Tuple[bool, float]:
        """
        Check if credit is available for a transaction.
        Returns (is_available, available_amount).
        """
        available = self.get_available_credit(driver_id=driver_id, agency_id=agency_id)
        return (available >= requested_amount, available)

    def update_agency_risk_metrics(
        self,
        agency_id: int,
        *,
        fleet_size: Optional[int] = None,
        average_repayment_days: Optional[float] = None,
        monthly_fuel_volume: Optional[float] = None,
    ) -> Agency:
        """
        Update agency risk metrics and recalculate risk score.
        """
        agency = self.db.get(Agency, agency_id)
        if not agency:
            raise ValueError("Agency not found")
        
        if fleet_size is not None:
            agency.fleet_size = fleet_size
        if average_repayment_days is not None:
            agency.average_repayment_days = average_repayment_days
        if monthly_fuel_volume is not None:
            agency.monthly_fuel_volume = monthly_fuel_volume
        
        # Recalculate risk score
        agency.risk_score = self.calculate_agency_risk_score(agency)
        
        self.db.commit()
        self.db.refresh(agency)
        return agency

