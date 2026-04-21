namespace McServerManager.Domain.ValueObjects;

public sealed record ValidationResult(IReadOnlyList<ValidationIssue> Issues)
{
    public bool IsValid => Issues.Count == 0;

    public static ValidationResult Success() => new([]);

    public static ValidationResult Failure(params ValidationIssue[] issues) => new(issues);
}

