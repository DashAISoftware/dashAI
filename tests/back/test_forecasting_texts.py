"""The texts forecasting shows in the app are spelled with their accents.

The components of forecasting reach the app in Spanish, Portuguese and German
through their ``MultilingualString``s: names, descriptions, and the titles and
descriptions of their parameters. Those were written without diacritics
("Origen Movil", "Numero de origenes", "rueckt"). This walks what the
components API serves for every forecasting component and fails on a word that
is only ever the unaccented spelling of another.

The lists are of whole words that are not words of their own in that
language, so a correct text never trips them. They name the forms the texts
had; they do not prove a text has every accent it needs.
"""

import re

import pytest

from DashAI.back.core.utils import MultilingualString, localize
from DashAI.back.initial_components import get_initial_components

FORECASTING_TASK = "SingleSeriesForecastingTask"
#: Forecasting components outside the forecasting modules.
NAMED = {
    FORECASTING_TASK,
    "RollingOriginSplitter",
    "TemporalHoldoutSplitter",
    "MAPE",
    "SMAPE",
}

UNACCENTED = {
    "es": {
        "mas",
        "ultimo",
        "ultimos",
        "ultima",
        "ultimas",
        "numero",
        "numeros",
        "origenes",
        "cuantos",
        "cuantas",
        "validacion",
        "evalua",
        "evaluan",
        "particion",
        "pronostico",
        "pronosticos",
        "movil",
        "moviles",
        "despues",
        "prediccion",
        "predicciones",
        "proporcion",
        "patron",
        "algun",
        "ordenes",
        "numerica",
        "numericas",
        "numerico",
        "numericos",
        "estacion",
        "tamano",
        "metrica",
        "metricas",
        "rapido",
        "util",
        "intervalo de prediccion",
        "historico",
        "historicos",
    },
    "pt": {
        "serie",
        "series",
        "previsao",
        "previsoes",
        "nao",
        "movel",
        "moveis",
        "historico",
        "historicos",
        "validacao",
        "particao",
        "particoes",
        "proporcao",
        "predicao",
        "media",
        "medio",
        "unica",
        "ultimo",
        "ultimos",
        "numero",
        "numeros",
        "avanca",
        "padrao",
        "distancia",
        "diarios",
        "proxima",
        "proximo",
        "variavel",
        "numerica",
        "propria",
        "periodo",
        "periodos",
        "mes",
        "disponivel",
        "comparavel",
        "metrica",
        "metricas",
        "estacao",
        "intervalo de predicao",
    },
    "de": {
        "rueckt",
        "fuer",
        "ueber",
        "naechste",
        "naechsten",
        "zurueck",
        "haelt",
        "laesst",
        "zaehlen",
        "jaehrlicher",
        "taegliche",
        "woechentlicher",
        "groesser",
        "groesse",
        "groessenordnung",
        "saisonlaenge",
        "aenderung",
        "schlaegt",
        "tatsaechlichen",
        "verfuegbar",
        "zukuenftigen",
        "fruehesten",
        "ursprunge",
        "einfliessen",
        "muessen",
        "koennen",
        "waehrend",
        "spaeter",
        "frueheren",
        "laenge",
        "verkuerze",
        "pruefe",
    },
}


def _forecasting_components():
    return sorted(
        (
            component
            for component in get_initial_components()
            if component.__name__ in NAMED or "forecast" in component.__module__
        ),
        key=lambda component: component.__name__,
    )


def _texts(value):
    """Every string in a localized structure."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _texts(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _texts(item)


def _served(component, lang):
    """What the app reads of a component in one language."""
    strings = [
        getattr(component, name)
        for name in dir(component)
        if isinstance(getattr(component, name, None), MultilingualString)
    ]
    texts = [string.get(lang) for string in strings]
    get_schema = getattr(component, "get_schema", None)
    if get_schema is not None:
        try:
            schema = get_schema()
        except Exception:  # a component without a schema of its own
            schema = None
        texts.extend(_texts(localize(schema, lang)))
    return texts


def _unaccented(text, lang):
    words = re.findall(r"[^\W\d_]+", text.lower())
    found = {word for word in words if word in UNACCENTED[lang]}
    found.update(
        phrase for phrase in UNACCENTED[lang] if " " in phrase and phrase in text
    )
    return sorted(found)


@pytest.mark.parametrize("lang", ["es", "pt", "de"])
@pytest.mark.parametrize(
    "component", _forecasting_components(), ids=lambda component: component.__name__
)
def test_a_forecasting_text_is_spelled_with_its_accents(component, lang):
    misspelled = {
        text: _unaccented(text, lang)
        for text in _served(component, lang)
        if _unaccented(text, lang)
    }

    assert misspelled == {}


def test_the_walk_reaches_every_forecasting_component():
    # Without it, a test over an empty list passes.
    names = {component.__name__ for component in _forecasting_components()}

    assert names >= NAMED
    assert {"ARIMA", "ForecastingHoldoutEvaluationStrategy"} <= names
