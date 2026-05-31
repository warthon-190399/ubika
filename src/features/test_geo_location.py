import pytest
from unittest.mock import MagicMock
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from geo_location import obtener_coordenadas


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def geolocator_mock():
    """Geolocator de Nominatim simulado."""
    return MagicMock()


def _resultado_valido(lat=-12.0464, lng=-77.0428):
    """Simula el objeto Location que devuelve geopy."""
    mock = MagicMock()
    mock.latitude = lat
    mock.longitude = lng
    return mock


# ─────────────────────────────────────────────
# Flujo exitoso
# ─────────────────────────────────────────────

def test_retorna_coordenadas_cuando_api_responde(geolocator_mock):
    """Debe retornar (lat, lng) cuando Nominatim encuentra la dirección."""
    geolocator_mock.geocode.return_value = _resultado_valido(lat=-12.0464, lng=-77.0428)

    lat, lng = obtener_coordenadas("Miraflores, Lima", geolocator_mock, contador=1)

    assert lat == pytest.approx(-12.0464)
    assert lng == pytest.approx(-77.0428)


def test_llama_geocode_con_la_direccion_correcta(geolocator_mock):
    """Debe pasar la dirección exacta al geolocator."""
    geolocator_mock.geocode.return_value = _resultado_valido()
    direccion = "Av. Larco 123, Miraflores"

    obtener_coordenadas(direccion, geolocator_mock, contador=1)

    geolocator_mock.geocode.assert_called_once_with(direccion)


def test_contador_none_no_rompe_ejecucion(geolocator_mock):
    """El parámetro contador es opcional; omitirlo no debe lanzar error."""
    geolocator_mock.geocode.return_value = _resultado_valido()

    lat, lng = obtener_coordenadas("Lima", geolocator_mock)

    assert lat is not None
    assert lng is not None


# ─────────────────────────────────────────────
# Sin resultados
# ─────────────────────────────────────────────

def test_retorna_none_none_cuando_no_hay_resultados(geolocator_mock):
    """Debe retornar (None, None) si Nominatim no encuentra la dirección."""
    geolocator_mock.geocode.return_value = None

    lat, lng = obtener_coordenadas("Dirección inexistente XYZ", geolocator_mock, contador=2)

    assert lat is None
    assert lng is None


# ─────────────────────────────────────────────
# Manejo de errores específicos de geopy
# ─────────────────────────────────────────────

def test_retorna_none_none_cuando_timeout(geolocator_mock):
    """Debe capturar GeocoderTimedOut y retornar (None, None)."""
    geolocator_mock.geocode.side_effect = GeocoderTimedOut("Timeout")

    lat, lng = obtener_coordenadas("Lima", geolocator_mock, contador=3)

    assert lat is None
    assert lng is None


def test_retorna_none_none_cuando_error_de_servicio(geolocator_mock):
    """Debe capturar GeocoderServiceError y retornar (None, None)."""
    geolocator_mock.geocode.side_effect = GeocoderServiceError("Servicio caído")

    lat, lng = obtener_coordenadas("Lima", geolocator_mock, contador=4)

    assert lat is None
    assert lng is None


def test_retorna_none_none_cuando_excepcion_inesperada(geolocator_mock):
    """Debe capturar cualquier otra excepción y retornar (None, None)."""
    geolocator_mock.geocode.side_effect = Exception("Error inesperado")

    lat, lng = obtener_coordenadas("Lima", geolocator_mock, contador=5)

    assert lat is None
    assert lng is None


def test_no_propaga_excepcion_al_caller(geolocator_mock):
    """La función no debe lanzar excepciones hacia afuera en ningún caso."""
    geolocator_mock.geocode.side_effect = RuntimeError("Fallo crítico")

    try:
        obtener_coordenadas("Lima", geolocator_mock, contador=6)
    except Exception:
        pytest.fail("obtener_coordenadas propagó una excepción inesperada")


# ─────────────────────────────────────────────
# Casos límite de entrada
# ─────────────────────────────────────────────

def test_direccion_cadena_vacia(geolocator_mock):
    """Una dirección vacía no debe romper la función."""
    geolocator_mock.geocode.return_value = None

    lat, lng = obtener_coordenadas("", geolocator_mock, contador=7)

    assert lat is None
    assert lng is None


def test_coordenadas_en_cero_son_validas(geolocator_mock):
    """Coordenadas (0.0, 0.0) son válidas y no deben tratarse como falsy."""
    geolocator_mock.geocode.return_value = _resultado_valido(lat=0.0, lng=0.0)

    lat, lng = obtener_coordenadas("Golfo de Guinea", geolocator_mock, contador=8)

    assert lat == 0.0
    assert lng == 0.0


def test_coordenadas_negativas_son_validas(geolocator_mock):
    """Coordenadas negativas (como Lima) deben retornarse correctamente."""
    geolocator_mock.geocode.return_value = _resultado_valido(lat=-12.0464, lng=-77.0428)

    lat, lng = obtener_coordenadas("Lima, Perú", geolocator_mock, contador=9)

    assert lat == pytest.approx(-12.0464)
    assert lng == pytest.approx(-77.0428)
