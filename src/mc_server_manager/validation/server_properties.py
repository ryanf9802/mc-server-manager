from __future__ import annotations

from mc_server_manager.domain.models import ValidationIssue, ValidationResult


class ServerPropertiesValidator:
    def validate(self, text: str) -> ValidationResult:
        issues: list[ValidationIssue] = []
        for index, line in enumerate(
            text.replace("\r\n", "\n").replace("\r", "\n").split("\n"), start=1
        ):
            if not line.strip():
                continue

            trimmed = line.lstrip()
            if trimmed.startswith("#") or trimmed.startswith("!"):
                continue

            if "=" not in line:
                issues.append(
                    ValidationIssue(
                        code="server_properties_missing_equals",
                        message=f"Line {index} must contain '=' or be a comment/blank line.",
                        line_number=index,
                    )
                )
        return ValidationResult(tuple(issues))
