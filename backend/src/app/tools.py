from langchain_core.tools import tool
from app.helpers import semantic_search, top_matches_from_metadata, safe_json_response, extract_email
from app.registry_api import lookup_registry, get_postal_code
from app.customer_api import (create_personal_customer, CreatePersonalCustomerRequestDto,
    PersonalIdentityDto,
    ContactInformationDto,
    AddressDto,
    CountryDto,
    LanguageDto,
    notify_branch,
    get_customer_by_external_key)

import json
import re
import sqlite3
from typing import List, Dict, Any


@tool
def vector_rag(query: str) -> str:
    """
    Retrieve business rules / policies from the knowledge base.
    Returns structured JSON: {"status":"ok","hits":[{...},...]} or {"status":"error", "message":...}
    """
    try:
        distances, indices = semantic_search(query, k=5)
        hits = top_matches_from_metadata(distances, indices, k=5)
        if not hits:
            return safe_json_response({"status": "ok", "hits": [], "message": "No relevant rules found."})
        # Return the textual snippets + source
        out = [{"chunk_id": h.get("chunk_id"), "source": h.get("source"), "text": h.get("text")} for h in hits]
        return safe_json_response({"status": "ok", "hits": out})
    except Exception as e:
        return safe_json_response({"status": "error", "message": str(e)})


@tool
def registry_lookup(inp: str) -> str:
    """
    Look up a person in the national registry.
    Input: "COUNTRY ID" (e.g., "DK 0101901234")

    Returns:
      {
        "status": "ok",
        "customer_status": "new" | "existing",
        "registry": { ... , "country": "...", "nationalId": "...", "externalKeyType": "..." }
      }
    """
    try:
        inp = inp.strip().strip('"').strip("'")
        if len(inp) < 4:
            return safe_json_response({"status": "error", "message": "Input too short for COUNTRY ID"})

        parts = inp.split(maxsplit=1)
        if len(parts) == 2:
            country, id_number = parts
        else:
            # Assume 2-letter country code
            country = inp[:2]
            id_number = inp[2:]
        country = country.upper()
        id_number = id_number.replace(" ", "").replace("-", "")
        match = re.search(r'\d+', id_number)
        id_number = match.group(0) if match else id_number

        if country not in ["DK", "SE", "NO", "FI"]:
            return safe_json_response({"status": "error", "message": f"Invalid country '{country}'. Allowed: DK, SE, NO, FI"})

        # mapping for externalKeyType
        key_type_map = {
            "DK": "DanishNationalId", # cprNumber
            "SE": "SwedishNationalId",
            "NO": "NorwegianNationalId",
            "FI": "FinnishNationalId"
        }
        external_key_type = key_type_map.get(country, "NationalId")

        # Lookup from mock registry
        result = lookup_registry(country, id_number)

        # Check if we already created this customer in DB
        existing = get_customer_by_external_key(id_number)
        customer_key = None
        if existing:
            # Extract customer key from DB
            conn = sqlite3.connect("database/customers.db")
            c = conn.cursor()
            c.execute("SELECT id, data FROM customers")
            rows = c.fetchall()
            conn.close()

            for row in rows:
                data = json.loads(row[1])
                try:
                    if data["identity"]["nationalId"] == id_number:
                        customer_key = row[0]
                        break
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
        return safe_json_response({
            "status": "ok",
            "customer_status": "existing" if existing else "new",
            "customerKey": customer_key,
            "registry": {
                "firstName": result.firstName,
                "lastName": result.lastName,
                "dateOfBirth": result.dateOfBirth,
                "gender": result.gender,
                "address": result.address,
                "maritalStatus": result.maritalStatus,
                "citizenship": result.citizenship,
                "residencePermitNumber": getattr(result, "residencePermitNumber", False),
                "country": country,
                "nationalId": id_number,
                "externalKeyType": external_key_type
            }
        })

    except Exception as e:
        return safe_json_response({"status": "error", "message": str(e)})


@tool
def verify_residence_permit(data: str) -> str:
    """
    Verify residence permit. Input: JSON string with user_input and expected_rp.
    Returns: JSON with verification result.
    """
    try:
        payload = json.loads(data)
        user_input = payload.get("user_input", "").strip()
        expected_rp = payload.get("expected_rp", "").strip()

        verified = (user_input == expected_rp)

        return json.dumps({
            "verified": verified,
            "user_input": user_input,
            "expected_rp": expected_rp
        })
    except Exception as e:
        return json.dumps({"verified": False, "error": str(e)})

@tool
def customer_create(data: str) -> str:
    """
    Create a new personal customer. This tool validates and normalizes input before calling the API.
    Accepts the same JSON you described, but also accepts a single-line address string and will attempt
    to convert it to AddressDto. Returns structured JSON with status.
    """
    try:
        payload = json.loads(data)
    except Exception as e:
        return safe_json_response({"status": "error", "message": f"invalid json: {e}"})

    missing = []
    identity = payload.get("identity")
    if not identity:
        return safe_json_response({"status": "incomplete", "missing": ["identity"]})

    # Required identity fields
    for f in ["country", "nationalId", "externalKeyType", "firstName", "lastName"]:
        if not identity.get(f):
            missing.append(f"identity.{f}")
    if missing:
        return safe_json_response({"status": "incomplete", "missing": missing})

    ext_key = identity["nationalId"]

    # Duplicate check
    if get_customer_by_external_key(ext_key):
        return safe_json_response({"status": "conflict", "message": f"Customer already exists with external key {ext_key}"})

    # Build PersonalIdentityDto (only allowed fields will be passed)
    identity_allowed = {
        "country": identity["country"],
        "nationalId": identity["nationalId"],
        "externalKeyType": identity["externalKeyType"],
        "firstName": identity.get("firstName"),
        "lastName": identity.get("lastName"),
        "dateOfBirth": identity.get("dateOfBirth"),
        "gender": identity.get("gender"),
        "address": identity.get("address"),
        "maritalStatus": identity.get("maritalStatus"),
        "citizenship": identity.get("citizenship"),
    }

    try:
        identity_dto = PersonalIdentityDto(**{k: v for k, v in identity_allowed.items() if v is not None})
    except Exception as e:
        return safe_json_response({"status": "error", "message": f"identity validation error: {e}"})

    # Handle contactInformation if provided
    contact_info = payload.get("contactInformation")
    ci_dto = None
    if contact_info:
        addr_list = contact_info.get("address")
        if not isinstance(addr_list, list) or len(addr_list) == 0:
            return safe_json_response({"status": "incomplete", "missing": ["contactInformation.address (list)"]})

        normalized_addresses = []
        for a in addr_list:
            # if already structured (dict), accept if minimal required present
            if isinstance(a, dict):
                try:
                    # ensure nested country & language objects exist
                    if "country" in a and isinstance(a["country"], dict):
                        a["country"] = CountryDto(**a["country"])
                    if "language" in a and isinstance(a["language"], dict):
                        a["language"] = LanguageDto(**a["language"])
                    addr_dto = AddressDto(**a)
                    normalized_addresses.append(addr_dto)
                    continue
                except Exception as e:
                    return safe_json_response({"status": "error", "message": f"address validation error: {e}"})

            # if a is a single-line string, attempt simple parse: "StreetName Nr, Postal City"
            if isinstance(a, str):
                try:
                    # crude parse: split on comma
                    parts = [p.strip() for p in a.split(",")]
                    street_part = parts[0] if parts else ""
                    postal_part = parts[1] if len(parts) > 1 else ""
                    # split street into name and house number
                    street_tokens = street_part.split()
                    if len(street_tokens) > 1:
                        houseNumber = street_tokens[-1]
                        streetName = " ".join(street_tokens[:-1])
                    else:
                        houseNumber = ""
                        streetName = street_part

                    postal_tokens = postal_part.split()
                    postalZone = postal_tokens[0] if postal_tokens else ""
                    cityName = " ".join(postal_tokens[1:]) if len(postal_tokens) > 1 else ""

                    addr_obj = {
                        "streetName": streetName or "UNKNOWN",
                        "houseNumber": houseNumber or "0",
                        "postalZone": postalZone or "",
                        "cityName": cityName or "",
                        "country": {"code": identity_dto.country},
                        "language": {"code": "da" if identity_dto.country == "DK" else "sv" if identity_dto.country == "SE" else "no" if identity_dto.country == "NO" else "fi"},
                        "primary": True,
                        "preferred": True
                    }
                    addr_dto = AddressDto(**addr_obj)
                    normalized_addresses.append(addr_dto)
                except Exception as e:
                    return safe_json_response({"status": "error", "message": f"address parsing error: {e}"})
            else:
                return safe_json_response({"status": "error", "message": "address must be dict or string"})

        # Build ContactInformationDto
        try:
            ci_dto = ContactInformationDto(address=normalized_addresses)
        except Exception as e:
            return safe_json_response({"status": "error", "message": f"contactInformation validation error: {e}"})

    # Create request DTO
    try:
        if ci_dto:
            request = CreatePersonalCustomerRequestDto(identity=identity_dto, contactInformation=ci_dto)
        else:
            request = CreatePersonalCustomerRequestDto(identity=identity_dto)
    except Exception as e:
        return safe_json_response({"status": "error", "message": f"request DTO error: {e}"})

    # Create the customer (calls app.customer_api.create_personal_customer)
    try:
        result = create_personal_customer(request)
        return safe_json_response({"status": "created", "customerKey": result.customerKey})
    except Exception as e:
        return safe_json_response({"status": "error", "message": str(e)})




@tool
def branch_lookup(inp: str) -> str:
    """
    Retrieve branch-related data. Returns JSON.
    """
    try:
        inp = inp.strip().strip('"').strip("'")
        distances, indices = semantic_search(inp, k=5)
        hits = top_matches_from_metadata(distances, indices, k=5)
        if not hits:
            return safe_json_response({"status": "ok", "hits": [], "message": "Branch information not found."})
        out = []
        for h in hits:
            out.append({
                "chunk_id": h.get("chunk_id"),
                "source": h.get("source"),
                "text": h.get("text"),
                "email": h.get("email"),
                "region": h.get("region"),
                "branch": h.get("branch")
            })
        return safe_json_response({"status": "ok", "hits": out})
    except Exception as e:
        return safe_json_response({"status": "error", "message": str(e)})


def get_tools():
    return [
    vector_rag,
    registry_lookup,
    verify_residence_permit,
    customer_create,
    branch_lookup,
            ]
