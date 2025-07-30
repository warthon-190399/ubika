# %% IMPORT LIBRARIES
import os
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.metrics import mean_absolute_percentage_error, mean_absolute_error
from sklearn.ensemble import RandomForestRegressor
from lightgbm import LGBMRegressor
from catboost import CatBoostRegressor
from xgboost import XGBRegressor
from sklearn.preprocessing import StandardScaler
import optuna
import joblib
import shap
#%%
def objective(trial):
    params = {"iterations":trial.suggest_int('iterations', 100, 1000),
            "depth": trial.suggest_int('depth', 4, 10),  # Profundidad del árbol
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
            'l2_leaf_reg': trial.suggest_float('l2_leaf_reg', 1e-3, 10, log=True),  # Regularización L2
            'random_strength': trial.suggest_float('random_strength', 1e-3, 10),  # Ruido para evitar overfitting
            'bagging_temperature': trial.suggest_float('bagging_temperature', 0.0, 1.0),  # Controla el muestreo de instancias
            'border_count': trial.suggest_int('border_count', 32, 255),  # Número de divisiones para variables numéricas
            'verbose': 0,
            'random_state': 42
                }
    model = CatBoostRegressor(**params)
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], early_stopping_rounds=50, verbose=False)
    y_pred = model.predict(X_test)
    return r2_score(y_test, y_pred)


# %% Read data
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
input_path = os.path.join(BASE_DIR, "data", "processed", "data_preprocessing_eng.csv")
output_path = os.path.join(BASE_DIR, "data", "processed", "final_dataset_l.csv")
output_model_path = os.path.join(BASE_DIR,"models","catboost_model_l.pkl")
output_hyperparams_path = os.path.join(BASE_DIR,"models","catboost_hyperparams_l.pkl")

# %%
df = pd.read_csv(input_path)

# data without 'miraflores', 'surco', 'san isidro','barranco'
df_modelling = df.copy()
df_modelling = df_modelling[~df_modelling['distrito'].isin(['miraflores', 'surco', 'san isidro','barranco'])]

print(df_modelling['distrito'].unique())

df_modelling = df_modelling.drop(["precio_usd","fecha_pub","distrito", 
                        "nivel_socioeconomico", "direccion_completa", 
                        "latitud", "longitud", "tamano", 
                        "num_comisarias_prox", 
                        "total_transporte_prox", "num_metro_est_prox", 
                        "num_malls_prox", "num_tren_est_prox", 
                        "zona_funcional"], axis=1) 
print(df_modelling.info())
# %% SPLIT DATA IN X AND Y
X = df_modelling.drop("precio_pen", axis=1)

y = df_modelling["precio_pen"]
X.columns
# %% Calculate the correlation matrix using only numeric columns
corr_matrix = X.corr(numeric_only=True)

plt.figure(figsize=(12, 8))
sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap='coolwarm', square=True, linewidths=0.5)
plt.title("Matriz de Correlación")
plt.tight_layout()
plt.show()


# %% SCALE OF VARIABLES

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# %% Split data in train and test
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)
# %% Dictionary of models
modelos = {
    "RandomForest": RandomForestRegressor(n_estimators=100, random_state=42),
    "XGBoost": XGBRegressor(n_estimators=100, random_state=42, verbosity=0),
    "LightGBM": LGBMRegressor(n_estimators=100, random_state=42),
    "CatBoost": CatBoostRegressor(verbose=0, random_state=42)
}

resultados = []

for nombre, modelo in modelos.items():

    modelo.fit(X_train, y_train)
    y_pred = modelo.predict(X_test)
    
    mae = mean_absolute_error(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    mape = mean_absolute_percentage_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_test, y_pred)

    resultados.append({
        "Modelo": nombre,
        "MAE": round(mae, 2),
        "MSE": round(mse, 2),
        "MAPE": round(mape * 100, 2),  # en porcentaje
        "RMSE": round(rmse, 2),
        "R2": round(r2, 4)
    })

df_resultados = pd.DataFrame(resultados).sort_values(by="R2", ascending=False).reset_index()
print(df_resultados)
#%%
study = optuna.create_study(direction='maximize')  # Queremos maximizar R²
study.optimize(objective, n_trials=50)  # Número de iteraciones

# Mejores parámetros
print("Mejores parámetros:", study.best_params)
print("Mejor R²:", study.best_value)

#%%
best_params = study.best_params

final_model = CatBoostRegressor(
    iterations=best_params['iterations'],
    depth=best_params['depth'],
    learning_rate=best_params['learning_rate'],
    l2_leaf_reg=best_params['l2_leaf_reg'],
    random_strength=best_params['random_strength'],
    bagging_temperature=best_params['bagging_temperature'],
    border_count=best_params['border_count'],
    verbose=0,
    random_state=42
)

final_model.fit(X_train,
                y_train,
                eval_set=[(X_test, y_test)],
                early_stopping_rounds=50
                )

y_pred = final_model.predict(X_test)
r2 = r2_score(y_test, y_pred)
print(f"R2 final: {r2:.4f}")


#%%
feature_importance = pd.DataFrame({
    'Feature': X.columns,
    'Importance': final_model.feature_importances_
}).sort_values(by='Importance', ascending=False)

print(feature_importance)

#%%
# Entrenar el modelo CatBoost (usa tus mejores hiperparámetros de Optuna)
final_model = CatBoostRegressor(**best_params, verbose=0, random_state=42)
final_model.fit(X_train, y_train)

# Calcula SHAP values para el conjunto de test
explainer = shap.Explainer(final_model)
shap_values = explainer(X_test)

# Resumen de importancia global (similar a feature_importance pero con dirección)
shap.summary_plot(shap_values, X_test, feature_names=X.columns)

# %%
joblib.dump(final_model, output_model_path)
joblib.dump(best_params, output_hyperparams_path)
# %%
df_modelling.to_csv(output_path, index=False)

# %%
