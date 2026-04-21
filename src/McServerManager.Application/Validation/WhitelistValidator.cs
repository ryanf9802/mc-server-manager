using System.Text.Json;
using McServerManager.Domain.ValueObjects;

namespace McServerManager.Application.Validation;

public sealed class WhitelistValidator : IWhitelistValidator
{
    public ValidationResult Validate(string text)
    {
        try
        {
            using var document = JsonDocument.Parse(text);
            if (document.RootElement.ValueKind != JsonValueKind.Array)
            {
                return ValidationResult.Failure(new ValidationIssue(
                    "whitelist_not_array",
                    "whitelist.json must contain a JSON array."));
            }

            var issues = new List<ValidationIssue>();
            var index = 0;
            foreach (var entry in document.RootElement.EnumerateArray())
            {
                if (entry.ValueKind != JsonValueKind.Object)
                {
                    issues.Add(new ValidationIssue(
                        "whitelist_entry_not_object",
                        $"Entry {index} must be a JSON object."));
                    index++;
                    continue;
                }

                if (!entry.TryGetProperty("name", out var nameProperty) || nameProperty.ValueKind != JsonValueKind.String)
                {
                    issues.Add(new ValidationIssue(
                        "whitelist_name_missing",
                        $"Entry {index} must contain a string 'name' property."));
                }

                if (!entry.TryGetProperty("uuid", out var uuidProperty) || uuidProperty.ValueKind != JsonValueKind.String)
                {
                    issues.Add(new ValidationIssue(
                        "whitelist_uuid_missing",
                        $"Entry {index} must contain a string 'uuid' property."));
                }

                index++;
            }

            return new ValidationResult(issues);
        }
        catch (JsonException exception)
        {
            return ValidationResult.Failure(new ValidationIssue(
                "whitelist_invalid_json",
                $"whitelist.json is not valid JSON: {exception.Message}"));
        }
    }
}

