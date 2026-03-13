"""
Pipeline principal del proyecto Ubika
Flujo:
Scraping → Processing → Preprocessing → Load
"""

# -------------------------
# IMPORTS
# -------------------------
from data.scraping.scraper_adondevivir import main as scraper_adondevivir
from data.scraping.scraper_adondevivir_detalles import main as scraper_adondevivir_detalles

from data.processing.process_adondevivir import main as process_adondevivir
from data.preprocessing.data_preprocessing import main as data_preprocessing

from features.feature_engineering import main as feature_engineering
from features.geo_location import main as geo_location
from features.proximidad_process import main as proximidad_process

from modeling.Compracion_de_modelos_l import main as Compracion_de_modelos_l
from modeling.Compracion_de_modelos_h import main as Compracion_de_modelos_h

# -------------------------
# PIPELINE
# -------------------------
def run_pipleline(run_scraping_1 = True, run_scraping_2 = True, run_processing_1 = True,
                  run_features_1 = True, run_features_2 = True, run_preprocessing_1=True,
                  run_features_3 = True, run_modeling_1 = True, run_modeling_2 = True):
    print("🚀 Iniciando pipeline Ubika...\n")
    
    # "SCRAPING"
    if run_scraping_1:
        print("Ejecutando scraper_adondevivir() ...")
        scraping_1 = scraper_adondevivir()
        # OUTPUT: "adondevivir_todas_las_paginas.csv"

    if run_scraping_2:
        print("Ejecutando scraper_adondevivir_detalles() ...")
        scraping_2 = scraper_adondevivir_detalles()
        # INPUT: "adondevivir_todas_las_paginas.csv"
        # OUTPUT: "adondevivir_todo3_completo.csv"
        # Ejecutar en horario de dormir

    # "PROCESSING"
    if run_processing_1:
        print("Ejecutando process_adondevivir() ...")
        processing_1 = process_adondevivir()
        # INPUT: "adondevivir_todo3_completo.csv"
        # OUTPUT: "adondevivir_processed.csv"

    # "FEATURES"
    if  run_features_1:
        print("Ejecutando geo_location() ...")
        features_1 = geo_location()
        # INPUT: "adondevivir_processed.csv"
        # OUTPUT: "adondevivir_processed_geo.csv"
        
    if run_features_2:
        print("Ejecutando proximidad_process() ...")
        features_2 = proximidad_process()
        # INPUT: "adondevivir_processed_geo.csv"
        # INPUT: "colegios_processed.csv"
        # INPUT: "hospitales_processed.csv"
        # OUTPUT: "proximidad_processed.csv"

    # "PREPROCESSING"
    if run_preprocessing_1:
        print("Ejecutando data_preprocessing() ...")
        preprocessing_1 = data_preprocessing()
        # INPUT: "proximidad_processed.csv"
        # OUTPUT: "data_preprocessing.csv"

    # "FEATURES"
    if run_features_3:
        print("Ejecutando feature_engineering() ...")
        features_3 = feature_engineering()
        # INPUT: "data_preprocessing.csv"
        # OUTPUT: "data_preprocessing_eng.csv"

    # "MODELING"
    if run_modeling_1:
        print("Ejecutando Compracion_de_modelos_l() ...")
        modeling_1 = Compracion_de_modelos_l()
        # INPUT: "data_preprocessing_eng.csv"
        # OUTPUT: "final_dataset_l.csv"
        # OUTPUT: "randomforest_model_l.pkl"
        # OUTPUT: "randomforest_hyperparams_l.pkl"
    
    if run_modeling_2:
        print("Ejecutando Compracion_de_modelos_h() ...")
        modeling_2 = Compracion_de_modelos_h()
        # INPUT: "data_preprocessing_eng.csv"
        # OUTPUT: "final_dataset_h.csv"
        # OUTPUT: "randomforest_model_h.pkl"
        # OUTPUT: "randomforest_hyperparams_h.pkl"
    
    print("Pipeline finalizado.")
# -------------------------
# ENTRY POINT
# -------------------------
if __name__ == "__main__":
    run_pipleline(run_scraping_1 = False, run_scraping_2 = False, run_processing_1 = False,
                  run_features_1 = False, run_features_2 = False, run_preprocessing_1=False,
                  run_features_3 = True, run_modeling_1 = False, run_modeling_2 = False)