using McServerManager.Domain.ValueObjects;

namespace McServerManager.Application.Validation;

public sealed class ServerPropertiesValidator : IServerPropertiesValidator
{
    public ValidationResult Validate(string text)
    {
        var issues = new List<ValidationIssue>();
        var lines = text.Replace("\r\n", "\n", StringComparison.Ordinal).Split('\n');

        for (var index = 0; index < lines.Length; index++)
        {
            var line = lines[index];
            if (string.IsNullOrWhiteSpace(line))
            {
                continue;
            }

            var trimmed = line.TrimStart();
            if (trimmed.StartsWith("#", StringComparison.Ordinal) || trimmed.StartsWith("!", StringComparison.Ordinal))
            {
                continue;
            }

            if (!line.Contains('='))
            {
                issues.Add(new ValidationIssue(
                    "server_properties_missing_equals",
                    $"Line {index + 1} must contain '=' or be a comment/blank line.",
                    index + 1));
            }
        }

        return new ValidationResult(issues);
    }
}
