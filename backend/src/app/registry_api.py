import json
import os
from pydantic import BaseModel
from typing import List, Union


class RegistryResponse(BaseModel):
    firstName: str
    lastName: str
    dateOfBirth: str
    gender: str
    address: str
    maritalStatus: str
    citizenship: List[str]
    residencePermitNumber: Union[str, bool, None] = False


# --------------------------
# MOCK NATIONAL REGISTRY DATA
# (Loaded from mock_data.json)
# --------------------------
MOCK_DATA = json.load(open(os.path.join(os.path.dirname(__file__), 'mock_data.json')))


# --------------------------
# API-LIKE LOOKUP FUNCTION
# --------------------------
def lookup_registry(country: str, id_number: str) -> RegistryResponse:
    """
    Simulates:
    GET https://{registry}/oplysninger/{id}
    """

    if country not in MOCK_DATA:
        raise ValueError(f"Unsupported country: {country}")

    if id_number not in MOCK_DATA[country]:
        raise ValueError(f"Invalid ID for {country}")

    data = MOCK_DATA[country][id_number]
    return RegistryResponse(**data)


def get_postal_code(address: str) -> str:
    """
    Extract postal code from an address string.
    Example: "Tokkerupvej 35, 2730 Herlev" -> "2730"
    """
    parts = address.split(',')
    if len(parts) > 1:
        return parts[1].strip().split()[0]
    return ""
