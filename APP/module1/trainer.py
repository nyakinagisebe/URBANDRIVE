import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
import joblib
import numpy as np

# 1. Load the Master Feature Matrix
df = pd.read_csv("master_training_features.csv")

# 2. Expert Logic: Calculate the "Investment Potential Score" (Target)
# I weight Jobs, Transport, and Retail higher for developers.
def calculate_investment_score(row):
    # Calculate average distances for key pillars
    job_dist = row[['dist_jobs_1', 'dist_jobs_2']].mean()
    trans_dist = row[['dist_transport_1', 'dist_transport_2']].mean()
    edu_dist = row[['dist_edu_1', 'dist_edu_2']].mean()
    retail_dist = row[['dist_retail_1', 'dist_retail_2']].mean()

    # Scoring Formula: Inverse distance (Closer = Higher Score)
    # We add 0.5km as a 'buffer' to prevent division by zero and dampen extreme proximity
    score = (
        (40 / (job_dist + 0.5)) +    # Employment is 40% of the weight
        (30 / (trans_dist + 0.3)) + # Transport is 30% of the weight
        (15 / (retail_dist + 0.5)) + # Retail is 15%
        (15 / (edu_dist + 1.0))      # Education is 15%
    )
    
    # Normalize to a 0-100 scale
    return min(100, score * 1.5)

print("--- Generating Investment Potential Targets ---")
df['investment_score'] = df.apply(calculate_investment_score, axis=1)

# 3. Prepare Data for the Extreme Gradient Boosting Regressor
X = df.drop(columns=['investment_score', 'lat', 'lon'])
y = df['investment_score']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 4. Training the Regressor
print("--- Training Extreme Gradient Boosting Regressor ---")
regressor = xgb.XGBRegressor(
    n_estimators=200,
    learning_rate=0.05,
    max_depth=6,
    objective='reg:squarederror',
    importance_type='gain'
)

regressor.fit(X_train, y_train)

# 5. Save the trained model for the App
joblib.dump(regressor, "nairobi_investment_model.pkl")
print("Success! Model saved as 'nairobi_investment_model.pkl'.")

# Show which features influenced the score the most
importances = pd.Series(regressor.feature_importances_, index=X.columns).sort_values(ascending=False)
print("\nTop Investment Drivers Identified by the Model:")
print(importances.head(5))