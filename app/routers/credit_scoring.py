"""
Credit Scoring API endpoints (AI-powered).
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.session import get_db
from app.services.credit_engine_service import CreditEngineService
from app.models.entities import Driver, Agency

router = APIRouter()


class ScoreRequest(BaseModel):
    driver_id: Optional[int] = None
    agency_id: Optional[int] = None


class ScoreResponse(BaseModel):
    trace_id: str
    driver_id: Optional[int] = None
    agency_id: Optional[int] = None
    risk_score: float
    risk_category: str
    credit_limit: float
    factors: dict


@router.post("/credit/score", response_model=ScoreResponse)
def score_credit(
    payload: ScoreRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    POST /credit/score
    Calculate credit score for driver or agency (AI-powered).
    """
    trace_id = getattr(request.state, "trace_id", "")
    credit_engine = CreditEngineService(db)
    
    if payload.driver_id:
        driver = db.get(Driver, payload.driver_id)
        if not driver:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Driver not found",
            )
        
        risk_category, limit = credit_engine.calculate_driver_risk_score(driver)
        
        # Convert category to score (simplified)
        score_map = {"LOW": 85.0, "MEDIUM": 65.0, "HIGH": 45.0}
        risk_score = score_map.get(risk_category, 65.0)
        
        factors = {
            "fuel_tank_capacity": float(driver.fuel_tank_capacity_liters) if driver.fuel_tank_capacity_liters else 60.0,
            "fuel_consumption": float(driver.fuel_consumption_l_per_km) if driver.fuel_consumption_l_per_km else 0.12,
            "vehicle_age": 2024 - driver.car_year if driver.car_year else None,
        }
        
        return ScoreResponse(
            trace_id=trace_id,
            driver_id=driver.id,
            risk_score=risk_score,
            risk_category=risk_category,
            credit_limit=limit,
            factors=factors,
        )
    
    elif payload.agency_id:
        agency = db.get(Agency, payload.agency_id)
        if not agency:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agency not found",
            )
        
        risk_score = credit_engine.calculate_agency_risk_score(agency)
        
        # Convert score to category
        if risk_score >= 75:
            category = "LOW"
            limit = 100000.0
        elif risk_score >= 50:
            category = "MEDIUM"
            limit = 50000.0
        else:
            category = "HIGH"
            limit = 25000.0
        
        factors = {
            "fleet_size": agency.fleet_size or 0,
            "average_repayment_days": float(agency.average_repayment_days) if agency.average_repayment_days else 30.0,
            "monthly_fuel_volume": float(agency.monthly_fuel_volume) if agency.monthly_fuel_volume else 0.0,
        }
        
        return ScoreResponse(
            trace_id=trace_id,
            agency_id=agency.id,
            risk_score=risk_score,
            risk_category=category,
            credit_limit=limit,
            factors=factors,
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either driver_id or agency_id must be provided",
        )


@router.get("/credit/explain/{driver_id}")
def explain_credit_score(
    driver_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    GET /credit/explain/{driver_id}
    Explain credit score calculation for a driver.
    """
    trace_id = getattr(request.state, "trace_id", "")
    credit_engine = CreditEngineService(db)
    
    driver = db.get(Driver, driver_id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found",
        )
    
    risk_category, limit = credit_engine.calculate_driver_risk_score(driver)
    
    # Detailed explanation
    capacity = driver.fuel_tank_capacity_liters or 60.0
    consumption = driver.fuel_consumption_l_per_km or 0.12
    est_monthly_liters = capacity * 8
    
    explanation = {
        "trace_id": trace_id,
        "driver_id": driver_id,
        "risk_category": risk_category,
        "credit_limit": limit,
        "explanation": {
            "fuel_tank_capacity": {
                "value": float(capacity),
                "impact": "LOW" if capacity <= 60 else "HIGH",
                "reason": "Smaller tanks indicate lower fuel consumption",
            },
            "fuel_consumption": {
                "value": float(consumption),
                "impact": "LOW" if consumption <= 0.1 else "HIGH",
                "reason": "Lower consumption per km indicates efficient vehicle",
            },
            "estimated_monthly_consumption": {
                "value": est_monthly_liters,
                "impact": "LOW" if est_monthly_liters <= 400 else "HIGH",
                "reason": "Estimated monthly fuel consumption based on tank capacity",
            },
            "risk_category_reason": f"Based on monthly consumption of {est_monthly_liters:.0f}L and consumption rate of {consumption:.2f}L/km",
        },
    }
    
    return explanation

