import math
from difflib import SequenceMatcher
from pathlib import Path
from unittest.mock import MagicMock
from tabulate import tabulate

from src.extractor import ClaimsExtractor
from src.schemas import ClaimRecord


def mock_response(content: str):
    choice = MagicMock()
    choice.message.content = content
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def Evaluator() -> str:
    client = MagicMock()
    base_dir = Path(__file__).resolve().parent

    extractor = ClaimsExtractor(client=client, max_retries=3)

    raw_claims_dir = base_dir.parent / "tests" / "evaluator_test_data" / "raw_claims"
    expected_outputs_dir = base_dir.parent / "tests" / "evaluator_test_data" / "expected_output"

    raw_claims = sorted(raw_claims_dir.glob("*.txt"))
    expected_outputs = sorted(expected_outputs_dir.glob("*.json"))

    data = []

    for i, file_path in enumerate(raw_claims):
        raw_json_expected = expected_outputs[i].read_text(encoding="utf-8")
        expected_record = ClaimRecord.model_validate_json(raw_json_expected)

        client.chat.completions.create.return_value = mock_response(raw_json_expected)

        raw_text = file_path.read_text(encoding="utf-8")
        response = extractor.extract(raw_text)

        # String similarity scores
        claim_id_score = SequenceMatcher(None, response.claim_id, expected_record.claim_id).ratio()
        provider_npi_score = SequenceMatcher(
            None, response.provider_npi, expected_record.provider_npi
        ).ratio()

        # Diagnosis code hallucinations (extracted codes not in ground truth)
        expected_diag_set = set(expected_record.diagnosis_codes)
        diagnoses_codes_hallucinations = sum(
            1 for code in response.diagnosis_codes if code not in expected_diag_set
        )

        # Line item charge inaccuracies
        charge_inaccuracies = 0
        min_items = min(len(response.line_items), len(expected_record.line_items))

        for idx in range(min_items):
            extracted_charge = response.line_items[idx].charge_amount
            expected_charge = expected_record.line_items[idx].charge_amount
            
            # Since charge_amount is Decimal, compare directly
            if extracted_charge != expected_charge:
                charge_inaccuracies += 1

        # Count any extra or missing line items as inaccuracies
        charge_inaccuracies += abs(len(response.line_items) - len(expected_record.line_items))

        data.append({
            "claim_id": expected_record.claim_id,
            "claim_id_score": round(claim_id_score, 2),
            "provider_npi_score": round(provider_npi_score, 2),
            "diagnoses_codes_hallucinations": diagnoses_codes_hallucinations,
            "charge_inaccuracies": charge_inaccuracies,
        })

    headers = {
        "claim_id": "Claim ID",
        "claim_id_score": "Claim ID Score",
        "provider_npi_score": "Provider NPI Score",
        "diagnoses_codes_hallucinations": "Diag Hallus",
        "charge_inaccuracies": "Charge Inaccuracies",
    }
    table = tabulate(data, headers=headers, tablefmt="grid")
    return table