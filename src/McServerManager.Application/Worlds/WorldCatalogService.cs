using McServerManager.Application.Activation;
using McServerManager.Domain.Models;
using McServerManager.Domain.ValueObjects;

namespace McServerManager.Application.Worlds;

public sealed class WorldCatalogService(
    IWorldRepository repository,
    ILiveConfigurationStore liveConfigurationStore,
    IHashService hashService) : IWorldCatalogService
{
    public async Task<IReadOnlyList<WorldSummary>> GetWorldsAsync(CancellationToken cancellationToken)
    {
        var manifests = await repository.ListWorldsAsync(cancellationToken);
        var activeRecord = await liveConfigurationStore.GetActiveWorldAsync(cancellationToken);
        var liveFiles = await liveConfigurationStore.GetLiveFilesAsync(cancellationToken);
        var liveHashes = ComputeHashes(liveFiles);

        var summaries = new List<WorldSummary>(manifests.Count);
        foreach (var manifest in manifests.OrderBy(world => world.DisplayName, StringComparer.OrdinalIgnoreCase))
        {
            var files = await repository.GetFilesAsync(manifest.Slug, cancellationToken)
                ?? throw new InvalidOperationException($"Managed world '{manifest.Slug}' is missing its files.");

            var status = ResolveStatus(manifest.Slug, files, activeRecord, liveHashes);
            summaries.Add(new WorldSummary(manifest, status));
        }

        return summaries;
    }

    public async Task<WorldDetail?> GetWorldAsync(string slug, CancellationToken cancellationToken)
    {
        var manifests = await repository.ListWorldsAsync(cancellationToken);
        var manifest = manifests.SingleOrDefault(world => string.Equals(world.Slug, slug, StringComparison.Ordinal));
        if (manifest is null)
        {
            return null;
        }

        var files = await repository.GetFilesAsync(slug, cancellationToken);
        if (files is null)
        {
            return null;
        }

        var activeRecord = await liveConfigurationStore.GetActiveWorldAsync(cancellationToken);
        var liveFiles = await liveConfigurationStore.GetLiveFilesAsync(cancellationToken);
        var liveHashes = ComputeHashes(liveFiles);
        var status = ResolveStatus(slug, files, activeRecord, liveHashes);

        return new WorldDetail(manifest, files, status);
    }

    private (string ServerPropertiesHash, string WhitelistHash) ComputeHashes(WorldFileSet files)
    {
        return (
            hashService.ComputeSha256(files.ServerPropertiesText),
            hashService.ComputeSha256(files.WhitelistJsonText));
    }

    private WorldStatus ResolveStatus(
        string slug,
        WorldFileSet managedFiles,
        ActiveWorldRecord? activeRecord,
        (string ServerPropertiesHash, string WhitelistHash) liveHashes)
    {
        if (activeRecord is null || !string.Equals(activeRecord.Slug, slug, StringComparison.Ordinal))
        {
            return WorldStatus.Inactive;
        }

        var liveMatchesPointer =
            string.Equals(activeRecord.ServerPropertiesSha256, liveHashes.ServerPropertiesHash, StringComparison.OrdinalIgnoreCase) &&
            string.Equals(activeRecord.WhitelistSha256, liveHashes.WhitelistHash, StringComparison.OrdinalIgnoreCase);

        if (!liveMatchesPointer)
        {
            return WorldStatus.UnmanagedLive;
        }

        var managedHashes = ComputeHashes(managedFiles);
        var managedMatchesLive =
            string.Equals(managedHashes.ServerPropertiesHash, liveHashes.ServerPropertiesHash, StringComparison.OrdinalIgnoreCase) &&
            string.Equals(managedHashes.WhitelistHash, liveHashes.WhitelistHash, StringComparison.OrdinalIgnoreCase);

        return managedMatchesLive ? WorldStatus.Active : WorldStatus.PendingApply;
    }
}

