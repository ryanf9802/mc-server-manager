namespace McServerManager.Domain.Models;

public sealed record ActiveWorldRecord(
    string Slug,
    DateTimeOffset AppliedAtUtc,
    string ServerPropertiesSha256,
    string WhitelistSha256);

