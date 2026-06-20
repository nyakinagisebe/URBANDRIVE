import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, r2_score

def train_model(file_paths):
    # 1. Load data
    dataframes = [pd.read_csv(f) for f in file_paths]
    df = pd.concat(dataframes, ignore_index=True)
    
    # 2. Cleaning
    df['price_ksh'] = pd.to_numeric(df['price_ksh'], errors='coerce')
    df = df.dropna(subset=['price_ksh'])
    df = df[(df['price_ksh'] >= 5000) & (df['price_ksh'] <= 100000000)] # Slightly wider range
    
    # 3. Target Encoding (The Accuracy Booster)
    # We calculate the mean price for each area and map it back
    for col in ['region_cluster', 'micro_area', 'topology']:
        df[col] = df[col].astype(str).str.upper().str.strip()
        encoding = df.groupby(col)['price_ksh'].mean().to_dict()
        df[f'{col}_avg_price'] = df[col].map(encoding)
        # Keep original as category
        df[col] = df[col].astype('category')

    features = [
        'region_cluster', 'micro_area', 'topology', 
        'region_cluster_avg_price', 'micro_area_avg_price', 'topology_avg_price',
        'borehole', 'parking', 'security'
    ]
    
    X = df[features]
    y = np.log1p(df['price_ksh'])
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # 4. Final XGBoost Configuration
    # We increase n_estimators but use a smaller learning_rate for precision
    model = XGBRegressor(
        n_estimators=1500,
        learning_rate=0.03,
        max_depth=8,  # Increased depth to capture neighborhood nuances
        subsample=0.9,
        colsample_bytree=0.9,
        enable_categorical=True,
        tree_method="hist",
        random_state=42
    )

    print("Training final refined model...")
    model.fit(X_train, y_train)
    
    # 5. Evaluation
    y_pred = model.predict(X_test)
    y_test_exp = np.expm1(y_test)
    y_pred_exp = np.expm1(y_pred)
    
    print(f"\n--- Refined Model Performance ---")
    print(f"MAE: KSh {mean_absolute_error(y_test_exp, y_pred_exp):,.2f}")
    print(f"R2 Score: {r2_score(y_test, y_pred):.4f}")
    
    joblib.dump(model, 'final_nairobi_price_model.joblib')
    return model

if __name__ == "__main__":
    files = ['nairobi_full_market_data2.csv', 'nairobi_comprehensive_dataset.csv', 'nairobi_market_dataset.csv']
    train_model(files)