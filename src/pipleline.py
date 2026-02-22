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
from data.scraping import scraper_properati

# -------------------------
# PIPELINE
# -------------------------
def run_pipleline():
    print("🚀 Iniciando pipeline Ubika...\n")
    raw_adondevivir = scraper_adondevivir()


# -------------------------
# ENTRY POINT
# -------------------------
if __name__ == "__main__":
    run_pipleline()