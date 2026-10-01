# Claims Extractor: Self-Healing Structured LLM Extraction

A CLI tool for parsing unstructured clinical notes and medical claim documents into strictly validated JSON records.

Designed to address the primary failure modes of LLMs in production: **non-determinism**, **malformed JSON**, and **schema hallucinations**. Instead of failing silently or discarding incomplete outputs, the extraction pipeline implements a multi-turn, bounded self-correction loop that feeds Pydantic v2 validation tracebacks directly back into the model context window.

---

## Key Mechanics

* **Strict Typing & Field Invariants (`pydantic` v2):** Enforces regex-validated ICD-10 diagnosis codes (`^[A-Z][0-9]{2}(\.[0-9A-Z]{1,4})?$`), 10-digit National Provider Identifiers (NPI), and positive decimal amounts for billed line items.
* **Bounded Self-Correction Loop:** Catches schema and JSON parsing exceptions programmatically. Each error message is injected as a corrective prompt in the conversational history (`user -> assistant -> user (feedback)`), guiding the model to self-heal up to a bounded maximum retry limit.
* **Controlled Failure Boundaries:** Raises explicit, domain-specific `ExtractionFailureError` exceptions containing full historical tracebacks when max retries are exceeded.
* **Local-First & Provider-Agnostic:** Built against the standard OpenAI Python SDK, pointed by default to a local [Ollama](https://ollama.com) instance to run open-weights models (`llama3.2`, `qwen2.5`) with zero API costs.
* **Deterministic Test Coverage:** Comprehensive unit tests using `pytest` and `unittest.mock.MagicMock` to simulate single-attempt recoveries, sequential failure repairs, and retry threshold limits without calling live models.

---

## System Architecture

```text
                       +-------------------+
                       | Raw Clinical Text |
                       +---------+---------+
                                 |
                                 v
                     +-----------------------+
                     |  Prompt Assembly &    |
                     | Injected JSON Schema  |
                     +-----------+-----------+
                                 |
                                 v
    +--------------+    +-----------------+
    |              |    | LLM Completion  | <----------+
    | Max Retries  |    | (Ollama/OpenAI) |            |
    |  Exhausted?  |    +--------+--------+            |
    |      |       |             |                     |
    |     Yes      |             v                     |
    |      v       |      Raw JSON Output              |
    | Raise Custom |             |                     |
    |    Error     |             v                     |
    |              |    +-----------------+            |
    |              |    | Pydantic Schema |            |
    |              |    |   Validation    |            |
    |              |    +--------+--------+            |
    |              |             |                     |
    |              |     [Validation Failed]           |
    |              |             |                     |
    +--------------+             v                     |
           ^             Format Traceback &            |
           |             Append Error Context          |
           +-------------+                             |
                   No    +-----------------------------+
                                 |
                          [Validation Passed]
                                 |
                                 v
                        +-----------------+
                        | Validated Model |
                        +-----------------+

```

---

## Tech Stack

* **Runtime:** Python 3.11+ (Tested on 3.12)
* **Package Management:** `uv`
* **Validation:** Pydantic v2
* **LLM Engine:** OpenAI Python SDK + Local Ollama
* **CLI & Output:** Typer, Rich
* **Testing:** Pytest

---

## Installation & Setup

### 1. Prerequisites

Install `uv`:

```powershell
choco install uv -y

```

Install and start [Ollama](https://ollama.com):

```powershell
choco install ollama -y
ollama pull llama3.2

```

### 2. Project Installation

Clone the repository and sync the virtual environment:

```powershell
git clone https://github.com/<your-username>/claims-extractor.git
cd claims-extractor

# Create virtualenv and install dependencies
uv sync

```

### 3. Environment Configuration

Default settings point to local Ollama. Set these in your shell or `.env` file if running elsewhere:

```powershell
$env:OPENAI_BASE_URL="http://localhost:11434/v1"
$env:OPENAI_API_KEY="ollama"
$env:CLAIM_MODEL="llama3.2"

```

---

## Usage

### Run CLI Extraction

Pass any raw, unstructured clinical or billing note to the CLI:

```powershell
uv run python -m src.cli sample_claim.txt

```

Options:

* `--max-retries <int>`: Set max retry cycles before raising controlled failure (Default: `3`).

### Example

**Input document:**

```text
Patient seen for routine diabetic check.
Claim CLM-492019 submitted by provider 1029384756.
Primary diagnosis: Type 2 diabetes with kidney complications (E11.22).
Procedures: Office visit (99214) at $215.50 and Blood glucose panel (82947) at $45.00.
Flag for manual duplicate review.

```

**CLI Output:**

```json
{
  "claim_id": "CLM-492019",
  "provider_npi": "1029384756",
  "diagnosis_codes": [
    "E11.22"
  ],
  "line_items": [
    {
      "service_code": "99214",
      "description": "Office visit",
      "charge_amount": "215.50"
    },
    {
      "service_code": "82947",
      "description": "Blood glucose panel",
      "charge_amount": "45.00"
    }
  ],
  "audit_flags": [
    "manual duplicate review"
  ]
}

```

---

## Running the Test Suite

The test suite verifies the retry engine using mocks without live LLM calls:

```powershell
uv run pytest -v

```

Tests verify:

* Valid payloads parse into schema objects without retrying.
* Invalid initial outputs trigger repair loops and successfully recover on subsequent turns.
* Exceeding the maximum retry count cleanly raises `ExtractionFailureError` with the aggregated errors.