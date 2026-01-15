question_schema = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": ["factual", "conceptual", "procedural"]
                    },
                    "difficulty": {
                        "type": "string",
                        "enum": ["grounded", "medium", "hard"]
                    },
                    "grounding_evidence": {"type": "string"}
                },
                "required": [
                    "question",
                    "type",
                    "difficulty",
                    "grounding_evidence"
                ],
                "additionalProperties": False
            }
        }
    },
    "required": ["questions"],
    "additionalProperties": False
}