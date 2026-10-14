import sys
from pathlib import Path

import pytest

# Ensure backend is on sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


from signalpost.config import settings


@pytest.fixture(autouse=True)
def disable_cache_for_tests(tmp_path):
    orig_cache = settings.cache_enabled
    orig_mistral_key = settings.mistral_api_key
    orig_api_key = settings.api_key
    settings.cache_enabled = False
    settings.mistral_api_key = ""
    settings.api_key = ""
    yield
    settings.cache_enabled = orig_cache
    settings.mistral_api_key = orig_mistral_key
    settings.api_key = orig_api_key


@pytest.fixture
def sample_brreg_entity_json():
    return {
        "organisasjonsnummer": "923609016",
        "navn": "EQUINOR ASA",
        "organisasjonsform": {
            "kode": "ASA",
            "beskrivelse": "Allment aksjeselskap",
            "_links": {"self": {"href": "https://data.brreg.no/enhetsregisteret/api/organisasjonsformer/ASA"}}
        },
        "registreringsdatoEnhetsregisteret": "1995-08-09",
        "registrertIMvaregisteret": True,
        "naeringskode1": {
            "beskrivelse": "Utvinning av råolje",
            "kode": "06.100"
        },
        "antallAnsatte": 21500,
        "forretningsadresse": {
            "land": "Norge",
            "landkode": "NO",
            "postnummer": "4035",
            "poststed": "STAVANGER",
            "adresse": ["Forusbeen 50"],
            "kommune": "STAVANGER",
            "kommunenummer": "1103"
        },
        "hjemmeside": "www.equinor.com",
        "konkurs": False,
        "underAvvikling": False,
        "underTvangsavviklingEllerTvangsopplosning": False,
        "maalform": "Bokmål"
    }


@pytest.fixture
def sample_brreg_roles_json():
    return {
        "rollegrupper": [
            {
                "type": {
                    "kode": "DAGL",
                    "beskrivelse": "Daglig leder / administrerende direktør"
                },
                "sistEndret": "2020-11-02",
                "roller": [
                    {
                        "type": {
                            "kode": "DAGL",
                            "beskrivelse": "Daglig leder"
                        },
                        "person": {
                            "fodselsdato": "1970-01-01",
                            "navn": {
                                "fornavn": "Anders",
                                "etternavn": "Opedal"
                            },
                            "erDød": False
                        },
                        "fratraadt": False,
                        "rekkefoelge": 1
                    }
                ]
            },
            {
                "type": {
                    "kode": "STYR",
                    "beskrivelse": "Styre"
                },
                "sistEndret": "2023-05-10",
                "roller": [
                    {
                        "type": {
                            "kode": "LEDE",
                            "beskrivelse": "Styrets leder"
                        },
                        "person": {
                            "fodselsdato": "1960-01-01",
                            "navn": {
                                "fornavn": "Jon Erik",
                                "etternavn": "Reinhardsen"
                            },
                            "erDød": False
                        },
                        "fratraadt": False,
                        "rekkefoelge": 1
                    }
                ]
            }
        ]
    }


@pytest.fixture
def sample_brreg_regnskap_json():
    return [
        {
            "id": 10001,
            "journalnr": "2024-998877",
            "regnskapstype": "SELSKAP",
            "virksomhet": {
                "organisasjonsnummer": "923609016",
                "organisasjonsform": "ASA"
            },
            "regnskapsperiode": {
                "fraDato": "2023-01-01",
                "tilDato": "2023-12-31"
            },
            "valuta": "NOK",
            "avviklingsregnskap": False,
            "resultatregnskapResultat": {
                "driftsresultat": {
                    "driftsinntekter": {
                        "sumDriftsinntekter": 1150000000000.0
                    },
                    "driftsresultat": 380000000000.0
                },
                "aarsresultat": 135000000000.0
            },
            "eiendeler": {
                "sumEiendeler": 1750000000000.0
            },
            "egenkapitalGjeld": {
                "egenkapital": {
                    "sumEgenkapital": 560000000000.0
                }
            }
        }
    ]
