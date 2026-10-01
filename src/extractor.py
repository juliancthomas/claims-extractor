import os
import json
from openai import OpenAI
from pydantic import ValidationError
from src.schemas import ClaimRecord

SYSTEM_PROMPT = """
You are a strict data-extraction engine.
Convert the provided medical claim text into a valid JSON object matching this schema:
{schema}

CRITICAL RULES:
- Output raw JSON only.
- Do not output markdown code blocks (no ```json).
- Never add commentary or explanations.
"""

class ExtractionFailureError(RuntimeError):
    def __init__(self, message: str, errors: list[str]):
        super().__init__(message)
        self.errors = errors

class ClaimsExtractor:
    def __init__(
        self,
        client: OpenAI | None = None,
        base_url: str | None = None,
        model: str | None = None,
        max_retries: int = 3,
    ):
        resolved_base_url = base_url or os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
        api_key = os.getenv("OPENAI_API_KEY", "ollama")

        self.client = client or OpenAI(base_url=resolved_base_url, api_key=api_key)
        self.model = model or os.getenv("CLAIM_MODEL", "llama3.2")
        self.max_retries = max_retries

    def extract(self, raw_text: str) -> ClaimRecord:
        schema_json = json.dumps(ClaimRecord.model_json_schema(), indent=2)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT.format(schema=schema_json)},
            {"role": "user", "content": f"Extract the following claim:\n\n{raw_text}"}
        ]

        validation_errors: list[str] = []

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.0,
                    response_format={"type": "json_object"}
                )
                raw_content = response.choices[0].message.content or ""
            except Exception as exc:
                validation_errors.append(f"Attempt {attempt} API failure: {exc}")
                continue

            # Record assistant's output to keep alternating conversation history intact
            messages.append({"role": "assistant", "content": raw_content})

            try:
                parsed_json = json.loads(raw_content)
                return ClaimRecord.model_validate(parsed_json)
            except (json.JSONDecodeError, ValidationError) as exc:
                err_msg = str(exc)
                validation_errors.append(f"Attempt {attempt} validation failure: {err_msg}")

                if attempt < self.max_retries:
                    feedback_prompt = (
                        f"Your output failed validation:\n{err_msg}\n\n"
                        "Return ONLY the corrected JSON object resolving all errors above."
                    )
                    messages.append({"role": "user", "content": feedback_prompt})

        raise ExtractionFailureError(
            f"Extraction failed after {self.max_retries} attempts.",
            errors=validation_errors
        )