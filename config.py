# config.py
SCRAPE_ANTIGUEDAD = True

# Properati
PROPERTY_TYPES = ["rent", "sale"]
SCRAPING_CONFIG = {
                  "adondevivir":{
                  "rent":{"url_template":"https://www.adondevivir.com/departamentos-en-alquiler-pagina-{page_num}-q-lima.html",
                        "page":5,
                        "folder":"adondevivir_rent"
                        },
                  "sale":{"url_template":"https://www.adondevivir.com/inmuebles-en-venta-pagina-{page_num}-q-lima.html",
                        "page":5,
                        "folder":"adondevivir_sale"
                        }
                  }
            }

# Habilitar graficos
ENABLE_PLOTS = False