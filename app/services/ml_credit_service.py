
import os
import joblib
import numpy as np
from typing import Dict, Any, List

class MlCreditService:
    def __init__(self, model_path: str = "app/services/credit_scoring_ml_model.pkl"):
        self.model_path = model_path
        self.model = None
        self.feature_names = []
        self._load_model()

    def _load_model(self):
        if not os.path.exists(self.model_path):
            print(f"WARNING: Model file not found at {self.model_path}")
            return
        
        try:
            model_data = joblib.load(self.model_path)
            self.model = model_data.get('model')
            self.feature_names = model_data.get('feature_names', [])
            print(f"✓ Model loaded: {len(self.feature_names)} features")
        except Exception as e:
            print(f"ERROR: Failed to load model: {e}")

    def _apply_credit_rules(self, prediction, confidence, monthly_income):
        # Business rules provided by user
        is_good = prediction == 1

        if is_good:
            if confidence > 0.9:
                risk_class = 'A'
                min_limit, max_limit = 8000, 10000
            elif confidence > 0.7:
                risk_class = 'B'
                min_limit, max_limit = 3000, 8000
            else:
                risk_class = 'C'
                min_limit, max_limit = 10, 3000
        else:
            risk_class = 'C'
            min_limit, max_limit = 10, 1000

        # Calculate limit
        range_size = max_limit - min_limit
        base_limit = min_limit + (range_size * confidence)

        # Adjust for income
        income_factor = min(1.5, monthly_income / 40000)
        credit_limit = base_limit * income_factor

        # Round
        if credit_limit < 100:
            credit_limit = round(credit_limit / 10) * 10
        elif credit_limit < 1000:
            credit_limit = round(credit_limit / 50) * 50
        else:
            credit_limit = round(credit_limit / 100) * 100

        credit_limit = max(min_limit, min(max_limit, credit_limit))

        return {
            'risk_class': risk_class,
            'credit_limit': round(credit_limit, 2),
            'confidence': confidence
        }

    def predict_credit_score(self, driver_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict credit score and limit for a driver.
        Expected driver_data keys should match training features or be mappable.
        """
        if not self.model:
            return {
                "error": "Model not loaded",
                "risk_class": "UNKNOWN",
                "credit_limit": 0,
                "confidence": 0,
                "prediction": 0
            }

        # Construct feature vector
        # We try to find each feature in driver_data. 
        # If missing, we might need default values. 
        # For now, let's assume 0 or handle key errors if strict.
        # But robust approach: use 0.0 for missing numeric features.
        
        feature_vector = []
        missing_features = []
        
        for feature in self.feature_names:
            if feature in driver_data:
                feature_vector.append(driver_data[feature])
            else:
                # specific handling for known mapped fields if names differ
                # e.g. 'age' vs 'driver_age'
                val = driver_data.get(feature, 0.0) 
                feature_vector.append(val)
                if feature not in driver_data:
                    missing_features.append(feature)
        
        if missing_features:
            print(f"WARNING: Missing features in input: {missing_features}")

        # Reshape for single prediction
        features_array = np.array(feature_vector).reshape(1, -1)
        
        try:
            prediction = self.model.predict(features_array)[0]
            probabilities = self.model.predict_proba(features_array)[0]
            confidence = probabilities[prediction]
            
            monthly_income = driver_data.get('monthly_income', 0)
            
            result = self._apply_credit_rules(prediction, confidence, monthly_income)
            result['prediction'] = int(prediction)
            result['probabilities'] = {
                'bad_credit': float(probabilities[0]),
                'good_credit': float(probabilities[1])
            }
            
            return result
            
        except Exception as e:
            print(f"Prediction error: {e}")
            return {
                "error": str(e),
                "risk_class": "ERROR",
                "credit_limit": 0
            }
