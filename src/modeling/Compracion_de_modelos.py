# %% IMPORT LIBRARIES
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.metrics import mean_absolute_percentage_error, mean_absolute_error
import os
# %% IMPORT LIBRARIES FOR MODELS
from sklearn.ensemble import RandomForestRegressor
from sklearn.ensemble import GradientBoostingRegressor
from lightgbm import LGBMRegressor
from catboost import CatBoostRegressor
from xgboost import XGBRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.svm import SVR
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.optimizers import Adam
# %% IMPORT LIBRARIES FOR GRAPHS
import seaborn as sns
import matplotlib.pyplot as plt
# %% Read data
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
input_path = os.path.join(BASE_DIR, "data", "processed", "data_preprocessing_eng.csv")

#output_path = os.path.join(BASE_DIR, "data", "processed", "malls_processed_format.csv")

if os.path.exists(input_path):
    df = pd.read_csv(input_path)
    print("Archivo leído correctamente")
    
else:
    print("❌ El archivo no se encuentra en la ruta especificada.")

#Keep only year and month, as house prices change at this temporal resolution
df_modelling = df.drop(["precio_usd","fecha_pub","distrito", "nivel_socioeconomico", "direccion_completa", "latitud", "longitud", "tamano", "antiguedad_categoria","precio_distrito_prom", "precio_rel_distrito", "precio_m2_distrito", "precio_m2_rel"], axis=1) 
#%%
# %% Calculate the correlation matrix using only numeric columns
corr_matrix = df_modelling.corr(numeric_only=True)

# Show a heatmap
plt.figure(figsize=(12, 8))
sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap='coolwarm', square=True, linewidths=0.5)
plt.title("Matriz de Correlación")
plt.tight_layout()
plt.show()

# %% SPLIT DATA IN X AND Y
X = df_modelling.drop("precio_pen", axis=1)
y = df_modelling["precio_pen"]
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
    "CatBoost": CatBoostRegressor(verbose=0, random_state=42),
    #"GradientBoost": GradientBoostingRegressor(n_estimators=100, random_state=42),
    #"KNN": KNeighborsRegressor(n_neighbors=5),
    #"SVR": SVR(),
    "NeuralNetwork": "keras_model"
}

# %% Results
resultados = []
# %% Training and evaluation
for nombre, modelo in modelos.items():
    if nombre == "NeuralNetwork":
        # Crear red neuronal simple
        nn = Sequential()
        nn.add(Dense(64, input_dim=X_train.shape[1], activation='relu'))
        nn.add(Dense(32, activation='relu'))
        nn.add(Dense(1))  # Salida para regresión

        nn.compile(optimizer=Adam(0.001), loss='mse')
        nn.fit(X_train, y_train, epochs=50, batch_size=8, verbose=0)

        y_pred = nn.predict(X_test).flatten()
    else:
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
        "R2 Score": round(r2, 4)
    })
# %% Show results
df_resultados = pd.DataFrame(resultados).sort_values(by="RMSE")
print(df_resultados)
# %%
from catboost import CatBoostRegressor
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import make_scorer, mean_squared_error
import numpy as np

# Definir modelo base (sin entrenar)
cat_model = CatBoostRegressor(verbose=0, random_state=42)

# Definir el grid de hiperparámetros
param_grid = {
    'iterations': [100, 200],
    'depth': [4, 6, 8],
    'learning_rate': [0.01, 0.05, 0.1],
    'l2_leaf_reg': [1, 3, 5]
}

# Definir el scoring (puedes usar R² o RMSE)
#scorer = make_scorer(mean_squared_error, greater_is_better=False)

# Configurar GridSearchCV
grid_search = GridSearchCV(
    estimator=cat_model,
    param_grid=param_grid,
    scoring="r2",        # Aquí usamos RMSE negativo
    cv=3,                  # 5-fold cross-validation
    n_jobs=-1              # Usa todos los núcleos disponibles
)

# Ejecutar la búsqueda de hiperparámetros
grid_search.fit(X_train, y_train)

# Mostrar mejores hiperparámetros
print("✅ Mejores hiperparámetros encontrados:")
print(grid_search.best_params_)

# Predecir y evaluar
best_cat_model = grid_search.best_estimator_
y_pred = best_cat_model.predict(X_test)

rmse = np.sqrt(mean_squared_error(y_test, y_pred))
print(f"📊 RMSE del mejor modelo CatBoost: {rmse:.2f}")
# %%
print("📈 Mejor R² obtenido:", grid_search.best_score_)
# %%
