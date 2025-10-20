import pandas as pd
import joblib
model = joblib.load("model02.pkl")
FEATURES = ["age", "rating"]


def est_cost_eur(age, rating):
    """Cost estimate using trained RandomForest model (euros)."""
    X = pd.DataFrame([[age, rating]], columns=FEATURES)
    raw = model.predict(X)[0]
    return max(int(round(raw)), 1)
