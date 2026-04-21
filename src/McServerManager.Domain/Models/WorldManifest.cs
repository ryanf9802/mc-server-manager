namespace McServerManager.Domain.Models;

public sealed record WorldManifest(
    string Slug,
    string DisplayName,
    DateTimeOffset CreatedAtUtc,
    DateTimeOffset UpdatedAtUtc);

