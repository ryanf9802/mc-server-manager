from __future__ import annotations

import json
from typing import cast

from mc_server_manager.domain.models import ValidationIssue, ValidationResult


class WhitelistValidator:
    def validate(self, text: str) -> ValidationResult:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            return ValidationResult(
                (
                    ValidationIssue(
                        code="whitelist_invalid_json",
                        message=f"whitelist.json is not valid JSON: {exc.msg}",
                    ),
                )
            )

        if not isinstance(payload, list):
            return ValidationResult(
                (
                    ValidationIssue(
                        code="whitelist_not_array",
                        message="whitelist.json must contain a JSON array.",
                    ),
                )
            )

        issues: list[ValidationIssue] = []
        for index, item in enumerate(payload):
            if not isinstance(item, dict):
                issues.append(
                    ValidationIssue(
                        code="whitelist_entry_not_object",
                        message=f"Entry {index} must be a JSON object.",
                    )
                )
                continue

            entry = cast(dict[str, object], item)

            if not isinstance(entry.get("name"), str):
                issues.append(
                    ValidationIssue(
                        code="whitelist_name_missing",
                        message=f"Entry {index} must contain a string 'name' property.",
                    )
                )

            if not isinstance(entry.get("uuid"), str):
                issues.append(
                    ValidationIssue(
                        code="whitelist_uuid_missing",
                        message=f"Entry {index} must contain a string 'uuid' property.",
                    )
                )

        return ValidationResult(tuple(issues))
