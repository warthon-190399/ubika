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
from data.preprocessing import data_preprocessing

# -------------------------
# PIPELINE
# -------------------------
def run_pipleline():
    print("🚀 Iniciando pipeline Ubika0...\n")
    
    # SCRAPING
    print("Scraper adondevivir")
    raw_adondevivir = scraper_adondevivir()

    print("Scraper adondevivir detalles")
    detalles_adondevivir = scraper_adondevivir_detalles()

    # PROCESSING
    print("Processing adondevivir")
    processing_adondevivir = process_adondevivir()

    # PREPROCESSING
    print("Preprocessing adondevivir")
    preprocessing_adondevivir = data_preprocessing()

# -------------------------
# ENTRY POINT
# -------------------------
if __name__ == "__main__":
    run_pipleline()