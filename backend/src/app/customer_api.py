import sqlite3
import json
import uuid
import os
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional, Union


# --------------------------
# DTO DEFINITIONS
# --------------------------

class CountryDto(BaseModel):
    code: str = Field(..., min_length=2, max_length=2)


class LanguageDto(BaseModel):
    code: str = Field(..., min_length=2, max_length=2)


class AddressDto(BaseModel):
    streetName: str
    houseNumber: str
    floor: Optional[str] = None
    side: Optional[str] = None
    room: Optional[str] = None
    postalZone: str
    cityName: str
    country: CountryDto
    language: LanguageDto
    primary: Optional[bool] = False
    preferred: Optional[bool] = False


class ContactInformationDto(BaseModel):
    address: List[AddressDto]


class PersonalIdentityDto(BaseModel):
    # Core minimal identity fields
    country: str = Field(..., min_length=2, max_length=2)      # e.g. "DK"
    nationalId: str = Field(..., min_length=1)                 # e.g. "0101901234"
    externalKeyType: str = Field(..., min_length=1)            # e.g. "DanishNationalId"

    # Optional enriched identity data
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    dateOfBirth: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    maritalStatus: Optional[str] = None
    citizenship: Optional[List[str]] = None
    residencePermitNumber: Union[str, bool, None] = False


class CreatePersonalCustomerRequestDto(BaseModel):
    identity: PersonalIdentityDto
    contactInformation: Optional[ContactInformationDto] = None


class CreateCustomerResponseDto(BaseModel):
    customerKey: str


# --------------------------
# DATABASE SETUP
# --------------------------
def init_db():
    os.makedirs("database", exist_ok=True)
    conn = sqlite3.connect("database/customers.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS customers
                 (id TEXT PRIMARY KEY, data TEXT)""")
    conn.commit()
    conn.close()


# --------------------------
# CREATE CUSTOMER (POST /customers/personal)
# --------------------------
def create_personal_customer(request: CreatePersonalCustomerRequestDto) -> CreateCustomerResponseDto:
    init_db()

    # --- emulate API returning 202 Accepted ---
    customer_key = str(uuid.uuid4())

    data = request.model_dump_json()
    conn = sqlite3.connect("database/customers.db")
    c = conn.cursor()
    c.execute("INSERT INTO customers (id, data) VALUES (?, ?)", (customer_key, data))
    conn.commit()
    conn.close()

    return CreateCustomerResponseDto(customerKey=customer_key)



# --------------------------
# FETCH CUSTOMER BY EXTERNAL KEY
# --------------------------
def get_customer_by_external_key(external_key: str) -> Optional[dict]:
    init_db()
    conn = sqlite3.connect("database/customers.db")
    c = conn.cursor()
    c.execute("SELECT data FROM customers")
    rows = c.fetchall()
    conn.close()

    for row in rows:
        data = json.loads(row[0])
        try:
            key = data["identity"]["nationalId"]
            if key == external_key:
                return data
        except KeyError:
            continue

    return None


# --------------------------
# MOCK NOTIFICATION SERVICE
# --------------------------
def notify_branch(customer_key: str, branch_email: str):
    # Simulated email sending
    print(f"[MOCK] Notification sent to {branch_email} for customer {customer_key}")
