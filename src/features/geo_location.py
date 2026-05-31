import pandas as pd
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from time import sleep
import os


def obtener_coordenadas(direccion, geolocator, contador=None):
    try:
        resultado = geolocator.geocode(direccion)
        if resultado:
            latitud = resultado.latitude
            longitud = resultado.longitude
            print(f"[{contador}] ✅ Coordenadas encontradas para: {direccion}")
            return latitud, longitud
        else:
            print(f"[{contador}] ⚠️ No se encontraron coordenadas para: {direccion}")
            return None, None
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"[{contador}] ❌ Error al geocodificar '{direccion}': {e}")
        return None, None
    except Exception as e:
        print(f"[{contador}] ❌ Error inesperado '{direccion}': {e}")
        return None, None


def main(folder_name):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
    input_path = os.path.join(BASE_DIR, "data", "processed", folder_name, f"{folder_name}_processed.csv")
    output_path = os.path.join(BASE_DIR, "data", "processed", folder_name, f"{folder_name}_processed_geo.csv")

    # Nominatim requiere un user_agent único para identificar tu app
    geolocator = Nominatim(user_agent="ubika_geo_app")

    df = pd.read_csv(input_path)

    latitudes = []
    longitudes = []

    for i, row in enumerate(df.itertuples(), start=1):
        direccion = row.direccion_completa
        if pd.isna(direccion):
            direccion = row.distrito

        lat, lon = obtener_coordenadas(direccion, geolocator, contador=i)
        latitudes.append(lat)
        longitudes.append(lon)
        sleep(1)  # Nominatim exige máximo 1 request/segundo

    df["latitud"] = latitudes
    df["longitud"] = longitudes

    df.to_csv(output_path, index=False)
    print(f"✅ Geocodificación finalizada. Archivo guardado en:\n{output_path}")


if __name__ == "__main__":
    main()
