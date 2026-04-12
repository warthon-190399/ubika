# config.py
SCRAPE_ANTIGUEDAD = False

# Properati
PROPERTY_TYPES = ["rent", "sale"]
PROPERTY_LINKS = {"rent":{"url_template":"https://www.adondevivir.com/departamentos-en-alquiler-pagina-{page_num}-q-lima.html",
                        "page":5},
                  "sale":{"url_template":"https://www.adondevivir.com/inmuebles-en-venta-pagina-{page_num}-q-lima.html",
                        "page":5}}

# Habilitar graficos
ENABLE_PLOTS = False