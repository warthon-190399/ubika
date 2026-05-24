# IMPORT LIBRARIES
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

def objective_rf(trial, X_train, y_train, X_test, y_test):
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 100, 500),
        "max_depth": trial.suggest_int("max_depth", 5, 30),
        "min_samples_split": trial.suggest_int("min_samples_split", 2, 10),
        "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 5),
        "max_features": trial.suggest_categorical("max_features", ["sqrt", "log2"])
    }

    model = RandomForestRegressor(**params)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    return r2_score(y_test, y_pred)

def objective_lgbm(trial, X_train, y_train, X_test, y_test):
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 100, 500),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2),
        "num_leaves": trial.suggest_int("num_leaves", 20, 150),
        "max_depth": trial.suggest_int("max_depth", 5, 20)
    }

    model = LGBMRegressor(**params)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    return r2_score(y_test, y_pred)

def objective_xgb(trial, X_train, y_train, X_test, y_test):
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 100, 500),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "max_depth": trial.suggest_int("max_depth", 3, 10),
        "subsample": trial.suggest_float("subsample", 0.5, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "gamma": trial.suggest_float("gamma", 0, 5),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 10, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10, log=True),
        "random_state": 42,
        "verbosity": 0
    }

    model = XGBRegressor(**params)

    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False
    )

    y_pred = model.predict(X_test)
    return r2_score(y_test, y_pred)

def objective_catboost(trial, X_train, y_train, X_test, y_test):
    params = {
        "iterations": trial.suggest_int("iterations", 300, 1000),
        "depth": trial.suggest_int("depth", 4, 10),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1e-3, 10, log=True),
        "random_strength": trial.suggest_float("random_strength", 1e-3, 10),
        "bagging_temperature": trial.suggest_float("bagging_temperature", 0.0, 1.0),
        "border_count": trial.suggest_int("border_count", 32, 255),
        "random_state": 42,
        "verbose": 0
    }

    model = CatBoostRegressor(**params)

    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        early_stopping_rounds=50,
        verbose=False
    )

    y_pred = model.predict(X_test)
    return r2_score(y_test, y_pred)

def main(folder_name, target, features, test_size, random_state, n_trials, enabled_models):

    # Read data
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
    
    input_path = os.path.join(BASE_DIR, "data", "processed", folder_name,f"{folder_name}_dataset_l.csv")
    output_path = os.path.join(BASE_DIR, "data", "processed", folder_name,f"{folder_name}_final_dataset_l.csv")
    output_model_path = os.path.join(BASE_DIR,"models",f"{folder_name}_best_model_l.pkl")
    output_hyperparams_path = os.path.join(BASE_DIR,"models",f"{folder_name}_best_hyperparams_l.pkl")
    results_path = os.path.join(BASE_DIR,"reports","metrics",folder_name)
    os.makedirs(results_path, exist_ok=True)

    df = pd.read_csv(input_path)

    df_modelling = df.copy()
    df_modelling = df[features + [target]]

    # Replace NaN in num_estac with zero
    df_modelling['num_estac'] = df_modelling['num_estac'].fillna(0)

    print(df_modelling.columns)
    # SPLIT DATA IN X AND Y
    
    X = df_modelling[features]
    y = df_modelling[target]

    X.columns
    # Calculate the correlation matrix using only numeric columns
    corr_matrix = X.corr(numeric_only=True)

    #if config.ENABLE_PLOTS:
    # Export correlation matrix
    figures_dir = os.path.join(BASE_DIR, "reports", "figures", folder_name)

    os.makedirs(figures_dir, exist_ok=True)

    plt.figure(figsize=(12, 8))
    sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap='coolwarm', square=True, linewidths=0.5)
    plt.title("Matriz de Correlación")
    plt.tight_layout()

    plt.savefig(
        os.path.join(BASE_DIR, "reports", "figures", folder_name, f"{folder_name}_corr_matrix_l.png"),
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

    # Split data in train and test
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state)
    
    # Dictionary of models
    modelos = {}

    if enabled_models.get("RandomForest", False):
        modelos["RandomForest"] = RandomForestRegressor(
            n_estimators=100,
            random_state=random_state
        )

    if enabled_models.get("XGBoost", False):
        modelos["XGBoost"] = XGBRegressor(
            n_estimators=100,
            random_state=random_state,
            verbosity=0
        )

    if enabled_models.get("LightGBM", False):
        modelos["LightGBM"] = LGBMRegressor(
            n_estimators=100,
            random_state=random_state
        )

    if enabled_models.get("CatBoost", False):
        modelos["CatBoost"] = CatBoostRegressor(
            verbose=0,
            random_state=random_state
        )

    if len(modelos) == 0:
        raise ValueError("No hay modelos habilitados en config.yaml")

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

    #df_resultados = pd.DataFrame(resultados).sort_values(by="R2", ascending=False).reset_index()
    df_resultados = pd.DataFrame(resultados).sort_values(by="R2", ascending=False).reset_index(drop=True)
    print(df_resultados)
    df_resultados.to_csv(
        os.path.join(results_path, f"{folder_name}_model_results_l.csv"),
        index=False
    )
    
    best_model_name = df_resultados.iloc[0]["Modelo"]

    print(f"Mejor modelo base: {best_model_name}")

    if best_model_name == "RandomForest":
        study = optuna.create_study(direction='maximize')  # Queremos maximizar R²
        study.optimize(
            lambda trial: objective_rf(trial, X_train, y_train, X_test, y_test),
            n_trials=n_trials
            )
        
        print(f"Modelo optimizado: {best_model_name}")
        print("Best params:", study.best_params)
        print("Best R2:", study.best_value)
        
        best_params = study.best_params
        final_model = RandomForestRegressor(**best_params, random_state=random_state)
        
    elif best_model_name == "XGBoost":
        study = optuna.create_study(direction='maximize')  # Queremos maximizar R²
        study.optimize(
            lambda trial: objective_xgb(trial, X_train, y_train, X_test, y_test),
            n_trials=n_trials
            )
        
        print(f"Modelo optimizado: {best_model_name}")
        print("Best params:", study.best_params)
        print("Best R2:", study.best_value)

        best_params = study.best_params
        final_model = XGBRegressor(**best_params, random_state=random_state, verbosity=0)

    elif best_model_name == "LightGBM":
        study = optuna.create_study(direction='maximize')  # Queremos maximizar R²
        study.optimize(
            lambda trial: objective_lgbm(trial, X_train, y_train, X_test, y_test),
            n_trials=n_trials
            )
        
        print(f"Modelo optimizado: {best_model_name}")
        print("Best params:", study.best_params)
        print("Best R2:", study.best_value)

        best_params = study.best_params
        final_model = LGBMRegressor(**best_params, random_state=random_state)

    elif best_model_name == "CatBoost":
        study = optuna.create_study(direction='maximize')  # Queremos maximizar R²
        study.optimize(
            lambda trial: objective_catboost(trial, X_train, y_train, X_test, y_test),
            n_trials=n_trials
            )
        
        print(f"Modelo optimizado: {best_model_name}")
        print("Best params:", study.best_params)
        print("Best R2:", study.best_value)

        best_params = study.best_params
        final_model = CatBoostRegressor(**best_params, verbose=0, random_state=random_state)

    # # Fit the CatBoost model with Optuna-optimized hyperparameters
    # final_model = CatBoostRegressor(**best_params, verbose=0, random_state=42)
    final_model.fit(X_train, y_train)

    # Calcula SHAP values para el conjunto de test
    if best_model_name in ["RandomForest", "XGBoost", "LightGBM", "CatBoost"]:
        explainer = shap.TreeExplainer(final_model)
    else:
        explainer = shap.Explainer(final_model)
    shap_values = explainer(X_test)

    #if config.ENABLE_PLOTS:
    # Exportar resumen de importancia global (similar a feature_importance pero con dirección)
    shap.summary_plot(
        shap_values, X_test, 
        feature_names=X.columns, 
        show=False
    )
    plt.savefig(
        os.path.join(BASE_DIR, "reports", "figures", folder_name, f"{folder_name}_shap_summary_l.png"),
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

    joblib.dump(final_model, output_model_path)
    joblib.dump(best_params, output_hyperparams_path)
    
    df_modelling.to_csv(output_path, index=False)

if __name__ == "__main__":
    main()