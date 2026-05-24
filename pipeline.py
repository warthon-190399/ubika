# -------------------------
# IMPORTS
# -------------------------
import yaml
import time

from src.data.scraping.scraper_adondevivir import main as scraper_adondevivir
from src.data.scraping.scraper_adondevivir_detalles import main as scraper_adondevivir_detalles

from src.data.processing.process_adondevivir import main as process_adondevivir
from src.data.preprocessing.data_preprocessing import main as data_preprocessing

from src.features.feature_engineering import main as feature_engineering
from src.features.geo_location import main as geo_location
from src.features.proximidad_process import main as proximidad_process

from src.data.splitting.dataset_split import main as dataset_split

from src.modeling.Comparacion_de_modelos_l import main as Comparacion_modelos_l
from src.modeling.Comparacion_de_modelos_h import main as Comparacion_modelos_h

# =========================
# LOAD YAML
# =========================
with open("configs/config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)


# -------------------------
# PIPELINE
# -------------------------
def run_pipeline():    
    inicio = time.perf_counter()

    print("🚀 Iniciando pipeline Ubika...\n")
    
    datasets_config = config["datasets"]
    pipeline_config = config["pipeline"]
    modeling_config = config["modeling"]

    for source, property_types in datasets_config.items():
        for property_type, settings in property_types.items():

            dataset_cfg = settings

            folder_name = dataset_cfg["folder"]

            scraping_cfg = dataset_cfg["scraping"]

            pages = scraping_cfg["pages"]
            url_template = scraping_cfg["url_template"]

            print(f"\n📦 Procesando: {folder_name}")

            # -------------------------
            # SCRAPING
            # -------------------------
            if pipeline_config["run_scraping"]:
                scraper_adondevivir(
                    pages=pages,
                    url_template=url_template,
                    output_file=paths["raw_file"]
                )

            if pipeline_config["run_scraping_details"]:
                scraper_adondevivir_detalles(
                    folder_name=folder_name,
                    input_path=config["paths"]["raw_data"],
                    output_path=config["paths"]["processed_data"]
                    )

            # -------------------------
            # PROCESSING
            # -------------------------
            if pipeline_config["run_processing"]:
                process_adondevivir(
                    folder_name=folder_name
                )

            # -------------------------
            # FEATURES
            # -------------------------
            if pipeline_config["run_geo"]:
                geo_location(folder_name=folder_name)

            if pipeline_config["run_proximidad"]:
                proximidad_process(folder_name=folder_name)

            if pipeline_config["run_preprocessing"]:
                data_preprocessing(folder_name=folder_name)

            if pipeline_config["run_feature_engineering"]:
                feature_engineering(folder_name=folder_name)

            if pipeline_config["run_splitting"]:
                dataset_split(folder_name=folder_name)

            # -------------------------
            # MODELING
            # -------------------------
            if pipeline_config["run_modeling_l"]:
                Comparacion_modelos_l(
                    folder_name=folder_name,
                    target=modeling_config["target"],
                    features=modeling_config["features"],
                    test_size=modeling_config["test_size"],
                    random_state=modeling_config["random_state"],
                    n_trials=modeling_config["n_trials"],
                    enabled_models=modeling_config["enabled_models"]
                )

            if pipeline_config["run_modeling_h"]:
                Comparacion_modelos_h(
                    folder_name=folder_name,
                    target=modeling_config["target"],
                    features=modeling_config["features"],
                    test_size=modeling_config["test_size"],
                    random_state=modeling_config["random_state"],
                    n_trials=modeling_config["n_trials"],
                    enabled_models=modeling_config["enabled_models"]
                )

    fin = time.perf_counter()

    print("Pipeline finalizado.")
    print(f"Tiempo de ejecución: {fin - inicio:.2f} segundos")
# -------------------------
# ENTRY POINT
# -------------------------
if __name__ == "__main__":
    run_pipeline()
