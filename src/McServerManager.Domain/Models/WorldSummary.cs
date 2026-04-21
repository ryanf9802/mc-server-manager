using McServerManager.Domain.ValueObjects;

namespace McServerManager.Domain.Models;

public sealed record WorldSummary(
    WorldManifest Manifest,
    WorldStatus Status);

