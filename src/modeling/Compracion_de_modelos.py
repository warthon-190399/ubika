# %% Import Libraries
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import os
# %% Models
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.svm import SVR
from sklearn.preprocessing import StandardScaler
# %% Read data
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
input_path = os.path.join(BASE_DIR, "data", "processed", "proximidad_processed.csv")

#output_path = os.path.join(BASE_DIR, "data", "processed", "malls_processed_format.csv")

if os.path.exists(input_path):
    df = pd.read_csv(input_path)
    print("Archivo leído correctamente")
    
else:
    print("❌ El archivo no se encuentra en la ruta especificada.")
# %%
df
# %% 
X = df.drop("precio_pen", axis=1)
y = df["precio_pen"]
# %% Scale of variables
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
# %% Split data in train and test
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)
# %% Dictionary of models
modelos = {
    "RandomForest": RandomForestRegressor(n_estimators=100, random_state=42),
    "XGBoost": XGBRegressor(n_estimators=100, random_state=42, verbosity=0),
    "KNN": KNeighborsRegressor(n_neighbors=5),
    "SVR": SVR(),
    "NeuralNetwork": "keras_model"  # Esto lo manejamos aparte
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
    
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    resultados.append({
        "Modelo": nombre,
        "RMSE": round(rmse, 2),
        "R2 Score": round(r2, 4)
    })
# %% Show results
df_resultados = pd.DataFrame(resultados).sort_values(by="RMSE")
print(df_resultados)