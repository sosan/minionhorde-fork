"""Generate 72 pending repetition records for cases 02, 04, and 06."""

import json
from pathlib import Path

CASES = [
    ("synthetic/sandbox-postcondition-001", "sandbox-postcondition-001"),
    ("synthetic/memory-injection-stale-approval-001", "memory-injection-stale-approval-001"),
    ("synthetic/approval-expiry-irreversible-001", "approval-expiry-irreversible-001"),
]
MODELS = ["claude-opus-5-max", "Anthropic"]
REPETITIONS = ["r01", "r02", "r03"]
CONDITIONS = ["C0", "C1", "C2", "C3"]
BASE_DIR = Path("docs/dogmas/eval/repetitions")


def create_pending_record(case_id: str, model: str, repetition_id: str, condition: str) -> dict:
    return {
        "schema_version": "manual-repetition-v1",
        "case_id": case_id,
        "case_version": "v1",
        "model": model,
        "repetition_id": repetition_id,
        "condition": condition,
        "response_literal": None,
        "status": "pending",
        "metadata": {
            "requested_model": model,
            "served_model": "unknown",
            "temperature": "unknown",
            "sampling": "unknown",
            "other_sampling": "unknown",
            "conversation_independent": "unknown",
            "label_or_id": f"{case_id}-v1",
            "operator_confirmed": False,
        },
        "classification": {"status": "pending", "classifier": None, "notes": "Awaiting literal response."},
        "evidence_limits": [
            "Sampling and temperature remain unknown unless directly recorded.",
            "Do not infer served_model from requested_model.",
            "Do not infer conversation independence from response wording.",
            "This record supports descriptive evidence only.",
        ],
    }


def main() -> None:
    count = 0
    for case_id, short in CASES:
        for model in MODELS:
            for repetition_id in REPETITIONS:
                for condition in CONDITIONS:
                    output_dir = BASE_DIR / short / model
                    output_dir.mkdir(parents=True, exist_ok=True)
                    output_file = output_dir / f"{repetition_id}-{condition}.json"
                    output_file.write_text(
                        json.dumps(create_pending_record(case_id, model, repetition_id, condition), indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                    count += 1
    print(f"Total records created: {count}")


if __name__ == "__main__":
    main()
