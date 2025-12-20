"""
Credit Scoring API endpoints (ML-powered).
"""
import uuid
from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from app.db.session import get_db
from app.services.ml_credit_service import MlCreditService
from app.models import Driver

router = APIRouter()

# Instantiate service once (global model load)
# In a real app, might want to do this on startup event or use a singleton dependency
ml_service = MlCreditService()


class ScoreRequest(BaseModel):
    driver_id: str # UUID as string
    # Financial features required by ML model (passed by caller, e.g. Bank)
    monthly_income: float = Field(..., description="Monthly income")
    account_age_months: int = Field(..., description="Age of account in months")
    avg_monthly_balance: float = Field(..., description="Average monthly balance")
    monthly_inflow_avg: float = Field(..., description="Average monthly inflow")
    monthly_outflow_avg: float = Field(..., description="Average monthly outflow")
    balance_trend_3m: float = Field(..., description="Balance trend over last 3 months")
    overdraft_count_6m: int = Field(..., description="Number of overdrafts in last 6 months")
    returned_payments_count: int = Field(..., description="Number of returned payments")
    age: int = Field(..., description="Driver age")


class ScoreResponse(BaseModel):
    trace_id: str
    driver_id: str
    risk_class: str
    credit_limit: float
    confidence: float
    prediction: int
    probabilities: Dict[str, float]
    factors: Dict[str, Any]


@router.post("/credit/score", response_model=ScoreResponse)
def score_credit(
    payload: ScoreRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    POST /credit/score
    Calculate credit score for driver using ML model.
    Combines DB driver info (car model) with provided financial info.
    """
    trace_id = getattr(request.state, "trace_id", "")
    
    driver = db.get(Driver, payload.driver_id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found",
        )
    
    # Prepare data for ML model
    # Combine payload (financials) + driver DB data (vehicle)
    driver_data = payload.dict()
    driver_data['car_model'] = driver.car_model or "Unknown"
    driver_data['car_year'] = driver.car_year or 2020
    
    # Call ML Service
    result = ml_service.predict_credit_score(driver_data)
    
    # Check for error
    if "error" in result:
        # In case of error (e.g. model missing), we return a safe fallback or error 
        # For now, let's just return what we got but maybe log it
        pass
        
    factors = {
        "car_model": driver_data['car_model'],
        "monthly_income": payload.monthly_income,
        "avg_monthly_balance": payload.avg_monthly_balance,
    }
    
    return ScoreResponse(
        trace_id=trace_id,
        driver_id=driver.id,
        risk_class=result.get("risk_class", "UNKNOWN"),
        credit_limit=result.get("credit_limit", 0.0),
        confidence=result.get("confidence", 0.0),
        prediction=result.get("prediction", 0),
        probabilities=result.get("probabilities", {"bad_credit": 0.0, "good_credit": 0.0}),
        factors=factors,
    )


@router.get("/credit/explain/{driver_id}")
def explain_credit_score(
    driver_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    GET /credit/explain/{driver_id}
    Explain credit capabilities. 
    Note: SHAP values not implemented yet, returning static info.
    """
    trace_id = getattr(request.state, "trace_id", "")
    
    return {
        "trace_id": trace_id,
        "message": "Detailed ML explanation (SHAP values) not yet implemented.",
        "model_features": ml_service.feature_names
    }

