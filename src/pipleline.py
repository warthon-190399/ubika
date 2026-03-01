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

from features import feature_engineering
from features import geo_location
from features import proximidad_process

from modeling import Compracion_de_modelos_l
from modeling import Compracion_de_modelos_h

# -------------------------
# PIPELINE
# -------------------------
def run_pipleline():
    print("🚀 Iniciando pipeline Ubika...\n")
    
    print("SCRAPING")
    scraping_1 = scraper_adondevivir()
    # OUTPUT: "adondevivir_todas_las_paginas.csv"

    scraping_2 = scraper_adondevivir_detalles()
    # INPUT: "adondevivir_todas_las_paginas.csv"
    # OUTPUT: "adondevivir_todo3_completo.csv"

    print("PROCESSING")
    processing_1 = process_adondevivir()
    # INPUT: "adondevivir_todo3_completo.csv"
    # OUTPUT: "adondevivir_processed.csv"

    print("FEATURES")
    features_1 = geo_location()
    # INPUT: "adondevivir_processed.csv"
    # OUTPUT: "adondevivir_processed_geo.csv"

    features_2 = proximidad_process()
    # INPUT: "adondevivir_processed_geo.csv"
    # INPUT: "colegios_processed.csv"
    # INPUT: "hospitales_processed.csv"
    # OUTPUT: "proximidad_processed.csv"

    print("PREPROCESSING")
    preprocessing_1 = data_preprocessing()
    # INPUT: "proximidad_processed.csv"
    # OUTPUT: "data_preprocessing.csv"

    print("FEATURES")
    features_3 = feature_engineering()
    # INPUT: "data_preprocessing.csv"
    # OUTPUT: "data_preprocessing_eng.csv"

    print("MODELING")
    modeling_1 = Compracion_de_modelos_l()
    # INPUT: "data_preprocessing_eng.csv"
    # OUTPUT: "final_dataset_l.csv"
    # OUTPUT: "randomforest_model_l.pkl"
    # OUTPUT: "randomforest_hyperparams_l.pkl"
    
    modeling_2 = Compracion_de_modelos_h()
    # INPUT: "data_preprocessing_eng.csv"
    # OUTPUT: "final_dataset_h.csv"
    # OUTPUT: "randomforest_model_h.pkl"
    # OUTPUT: "randomforest_hyperparams_h.pkl"

# -------------------------
# ENTRY POINT
# -------------------------
if __name__ == "__main__":
    run_pipleline()