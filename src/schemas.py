from decimal import Decimal
from typing import Annotated
from pydantic import BaseModel, Field, StringConstraints

# Standard ICD-10 format: letter followed by 2 digits, optional dot and up to 4 alphanumeric chars
ICD10Code = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Z][0-9]{2}(\.[0-9A-Z]{1,4})?$")
]

class LineItem(BaseModel):
    service_code: str = Field(..., description="CPT or HCPCS code, e.g., '99213'")
    description: str = Field(..., min_length=3)
    charge_amount: Decimal = Field(..., gt=Decimal("0.00"), decimal_places=2)

class ClaimRecord(BaseModel):
    claim_id: str = Field(..., pattern=r"^CLM-\d{4,8}$", description="e.g. CLM-102938")
    provider_npi: str = Field(..., pattern=r"^\d{10}$", description="10-digit National Provider Identifier")
    diagnosis_codes: list[ICD10Code] = Field(..., min_length=1)
    line_items: list[LineItem] = Field(..., min_length=1)
    audit_flags: list[str] = Field(default_factory=list)

class ExtractionResult():
    record: ClaimRecord
    latency_ms: float
    attempts_used: int
    token_usage: dict