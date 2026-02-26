"""
Pipeline principal del proyecto Ubika
Flujo:
Scraping → Processing → Preprocessing → Load
"""

# -------------------------
# IMPORTS
# -------------------------
from data.scraping import scraper_adondevivir
from data.scraping import scraper_adondevivir_detalles
from data.processing import process_adondevivir

# PROCESS 1
from data.preprocessing import data_preprocessing
from features import feature_engineering

# PROCESS 2
from features import geo_location

# -------------------------
# PIPELINE
# -------------------------
def run_pipleline():
    print("🚀 Iniciando pipeline Ubika...\n")
    
    # SCRAPING
    print("Scraper adondevivir")
    raw_adondevivir = scraper_adondevivir()

    print("Scraper adondevivir detalles")
    detalles_adondevivir = scraper_adondevivir_detalles()

    # PROCESSING
    print("Processing adondevivir")
    processing_adondevivir = process_adondevivir()

    # PROCCES 1
    print("# 1 Preprocessing adondevivir")
    preprocessing_adondevivir = data_preprocessing()

    print("# 1 Feature engineering")
    feature_engineering_pipleline = feature_engineering()

    # PROCCES 2, directions with google
    print("# 2 geo location")
    geo_location_pipleline = geo_location()


# -------------------------
# ENTRY POINT
# -------------------------
if __name__ == "__main__":
    run_pipleline()