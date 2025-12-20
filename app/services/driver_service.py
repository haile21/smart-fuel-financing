from __future__ import annotations

from typing import Tuple

from sqlalchemy.orm import Session

from app.models import Driver, Bank, User, UserRole



class DriverService:
    """
    Handles onboarding and simple risk scoring for drivers.
    """

    def __init__(self, db: Session):
        self.db = db

    def _compute_risk_and_limit(
        self,
        *,
        fuel_tank_capacity_liters: float | None,
        fuel_consumption_l_per_km: float | None,
    ) -> Tuple[str, float]:
        """
        Extremely simplified heuristic:
        - Low: small tank / modest consumption
        - Medium: default
        - High: very large tank / very high consumption
        """
        # Reasonable defaults if data missing
        capacity = fuel_tank_capacity_liters or 60.0
        consumption = fuel_consumption_l_per_km or 0.12  # 12L / 100km

        # monthly estimated liters ~ capacity * 8 fills / month as a simple proxy
        est_monthly_liters = capacity * 8

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

    def onboard_driver(
        self,
        *,
        phone_number: str,
        national_id: str,
        name: str,
        car_model: str | None,
        car_year: int | None,
        fuel_tank_capacity_liters: float | None,
        fuel_consumption_l_per_km: float | None,
        driver_license_number: str | None,
        plate_number: str | None,
        bank_id: int,
        consent_data_sharing: bool,
    ) -> Driver:
        # Ensure selected bank exists
        bank = self.db.get(Bank, bank_id)
        if not bank:
            raise ValueError("Selected bank does not exist")

        # If driver already exists, return existing (idempotent by phone_number)
        existing = (
            self.db.query(Driver)
            .filter(Driver.phone_number == phone_number)
            .one_or_none()
        )
        if existing:
            return existing

        risk_category, limit = self._compute_risk_and_limit(
            fuel_tank_capacity_liters=fuel_tank_capacity_liters,
            fuel_consumption_l_per_km=fuel_consumption_l_per_km,
        )

        driver = Driver(
            name=name,
            phone_number=phone_number,
            national_id=national_id,
            car_model=car_model,
            car_year=car_year,
            fuel_tank_capacity_liters=fuel_tank_capacity_liters,
            fuel_consumption_l_per_km=fuel_consumption_l_per_km,
            driver_license_number=driver_license_number,
            plate_number=plate_number,
            preferred_bank_id=bank_id,
            consent_data_sharing=consent_data_sharing,
            risk_category=risk_category,
        )
        self.db.add(driver)
        self.db.flush()  # populate driver.id

        # CreditLine creation removed (CreditLine deprecated)

        
        # Automatically create User account for driver
        user = User(
            phone_number=driver.phone_number,
            role=UserRole.DRIVER.value,
            driver_id=driver.id,
            is_active=True,
            is_verified=False,  # Requires OTP verification
        )
        self.db.add(user)
        self.db.commit()

        return driver


