from unittest.mock import MagicMock
import json
import pytest
from src.extractor import ClaimsExtractor, ExtractionFailureError
from src.schemas import ClaimRecord

def mock_response(content: str):
    choice = MagicMock()
    choice.message.content = content
    resp = MagicMock()
    resp.choices = [choice]
    return resp

def test_extractor_self_heals_invalid_schema():
    client = MagicMock()
    
    # Attempt 1: bad NPI (not 10 digits) and bad ICD-10
    bad_data = {
        "claim_id": "CLM-12345",
        "provider_npi": "123",
        "diagnosis_codes": ["invalid"],
        "line_items": [{"service_code": "99213", "description": "Consult", "charge_amount": "100.00"}]
    }
    # Attempt 2: valid
    good_data = {
        "claim_id": "CLM-12345",
        "provider_npi": "1234567890",
        "diagnosis_codes": ["E11.9"],
        "line_items": [{"service_code": "99213", "description": "Consult", "charge_amount": "100.00"}]
    }

    client.chat.completions.create.side_effect = [
        mock_response(json.dumps(bad_data)),
        mock_response(json.dumps(good_data))
    ]

    extractor = ClaimsExtractor(client=client, max_retries=3)
    record = extractor.extract("Some text")

    assert isinstance(record, ClaimRecord)
    assert record.provider_npi == "1234567890"
    assert client.chat.completions.create.call_count == 2

def test_extractor_fails_after_max_retries():
    client = MagicMock()
    client.chat.completions.create.return_value = mock_response("not even json")

    extractor = ClaimsExtractor(client=client, max_retries=3)
    with pytest.raises(ExtractionFailureError) as exc_info:
        extractor.extract("Unparseable")

    assert len(exc_info.value.errors) == 3