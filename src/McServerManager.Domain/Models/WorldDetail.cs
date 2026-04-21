using McServerManager.Domain.ValueObjects;

namespace McServerManager.Domain.Models;

public sealed record WorldDetail(
    WorldManifest Manifest,
    WorldFileSet Files,
    WorldStatus Status);

