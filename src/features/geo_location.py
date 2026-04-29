#
import pandas as pd
import googlemaps
from time import sleep
from dotenv import load_dotenv
import os
import config

def obtener_coordenadas(direccion, gmaps, contador=None):
    try:
        resultado = gmaps.geocode(direccion)
        if resultado:
            latitud = resultado[0]["geometry"]["location"]["lat"]
            longitud = resultado[0]["geometry"]["location"]["lng"]
            print(f"[{contador}] ✅ Coordenadas encontradas para: {direccion}")
            return latitud, longitud
        else:
            print(f"[{contador}] ⚠️ No se encontraron coordenadas para: {direccion}")
            return None, None
    except Exception as e:
        print(f"[{contador}] ❌ Error al geocodificar '{direccion}': {e}")
        return None, None

def main():
    for source, properaty_type in config.SCRAPING_CONFIG.items():
        for property_type, settings in properaty_type.items():
            new_folder = settings["folder"]


            # Read .env.example
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
            ENV_PATH = os.path.join(BASE_DIR, ".env")
            input_path = os.path.join(BASE_DIR, "data", "processed",new_folder,f"{new_folder}_processed.csv")
            output_path = os.path.join(BASE_DIR, "data", "processed",new_folder,f"{new_folder}_processed_geo.csv")

            load_dotenv(ENV_PATH)
            API_KEY = os.getenv("GOOGLE_GEOENCODING_APIKEY").strip().replace('"','').replace("'",'')

            gmaps = googlemaps.Client(key=API_KEY)

            df = pd.read_csv(input_path)

            # Aplicar geocodificación con contador
            latitudes = []
            longitudes = []

            for i, row in enumerate(df.itertuples(), start=1):
                direccion = row.direccion_completa
                if pd.isna(direccion):
                    direccion = row.distrito
                lat, lon = obtener_coordenadas(direccion, gmaps, contador=i)
                latitudes.append(lat)
                longitudes.append(lon)
                sleep(1)

            # Asignar al DataFrame
            df["latitud"] = latitudes
            df["longitud"] = longitudes

            df.to_csv(output_path, index = False)

if __name__ == "__main__":
    main()