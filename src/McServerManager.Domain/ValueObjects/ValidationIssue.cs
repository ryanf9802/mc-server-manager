namespace McServerManager.Domain.ValueObjects;

public sealed record ValidationIssue(
    string Code,
    string Message,
    int? LineNumber = null);

