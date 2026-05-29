from pathlib import Path


def build_paths(config, source, property_type):
    """
    Construye todas las rutas asociadas a un dataset.

    Parameters
    ----------
    config : dict
        Configuración cargada desde YAML.

    source : str
        Ejemplo: "adondevivir"

    property_type : str
        Ejemplo: "rent" o "sale"

    Returns
    -------
    dict
        Diccionario con carpetas y archivos.
    """

    dataset_cfg = config["datasets"][source][property_type]
    files_cfg = config["defaults"]["files"]
    paths_cfg = config["paths"]

    folder = dataset_cfg["folder"]

    # Carpetas
    raw_folder = Path(paths_cfg["raw_data"]) / folder
    processed_folder = Path(paths_cfg["processed_data"]) / folder

    # Crear carpetas si no existen
    raw_folder.mkdir(parents=True, exist_ok=True)
    processed_folder.mkdir(parents=True, exist_ok=True)

    return {
        "folder": folder,

        "raw_folder": raw_folder,
        "processed_folder": processed_folder,

        "raw_file": raw_folder / files_cfg["raw"].format(folder=folder),

        "processed_file": processed_folder / files_cfg["processed"].format(folder=folder),

        "geo_file": processed_folder / files_cfg["geo"].format(folder=folder),

        "features_file": processed_folder / files_cfg["features"].format(folder=folder),

        "train_file": processed_folder / files_cfg["train"].format(folder=folder),

        "test_file": processed_folder / files_cfg["test"].format(folder=folder),
    }