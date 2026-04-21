using McServerManager.Application.Validation;
using McServerManager.Domain.Models;

namespace McServerManager.Application.Worlds;

public sealed class WorldEditorService(
    IWorldRepository repository,
    ILiveConfigurationStore liveConfigurationStore,
    IServerPropertiesValidator serverPropertiesValidator,
    IWhitelistValidator whitelistValidator) : IWorldEditorService
{
    public async Task<WorldDetail> CreateDraftFromLiveAsync(string displayName, CancellationToken cancellationToken)
    {
        var existingWorlds = await repository.ListWorldsAsync(cancellationToken);
        var baseSlug = WorldNameGenerator.CreateSlug(displayName);
        var slug = EnsureUniqueSlug(baseSlug, existingWorlds.Select(world => world.Slug));

        var liveFiles = await liveConfigurationStore.GetLiveFilesAsync(cancellationToken);
        var manifest = new WorldManifest(
            slug,
            displayName.Trim(),
            DateTimeOffset.UtcNow,
            DateTimeOffset.UtcNow);

        return new WorldDetail(manifest, liveFiles, Domain.ValueObjects.WorldStatus.Inactive);
    }

    public async Task SaveWorldAsync(WorldDetail detail, CancellationToken cancellationToken)
    {
        var serverPropertiesValidation = serverPropertiesValidator.Validate(detail.Files.ServerPropertiesText);
        if (!serverPropertiesValidation.IsValid)
        {
            throw new InvalidOperationException(string.Join(Environment.NewLine, serverPropertiesValidation.Issues.Select(issue => issue.Message)));
        }

        var whitelistValidation = whitelistValidator.Validate(detail.Files.WhitelistJsonText);
        if (!whitelistValidation.IsValid)
        {
            throw new InvalidOperationException(string.Join(Environment.NewLine, whitelistValidation.Issues.Select(issue => issue.Message)));
        }

        var manifests = await repository.ListWorldsAsync(cancellationToken);
        var duplicate = manifests
            .Where(world => !string.Equals(world.Slug, detail.Manifest.Slug, StringComparison.Ordinal))
            .Any(world => string.Equals(world.DisplayName, detail.Manifest.DisplayName, StringComparison.OrdinalIgnoreCase));

        if (duplicate)
        {
            throw new InvalidOperationException($"A world named '{detail.Manifest.DisplayName}' already exists.");
        }

        var updatedManifest = detail.Manifest with
        {
            DisplayName = detail.Manifest.DisplayName.Trim(),
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };

        var normalizedFiles = new WorldFileSet(
            NormalizeLineEndings(detail.Files.ServerPropertiesText),
            NormalizeLineEndings(detail.Files.WhitelistJsonText));

        await repository.SaveWorldAsync(updatedManifest, normalizedFiles, cancellationToken);
    }

    public async Task DeleteWorldAsync(string slug, CancellationToken cancellationToken)
    {
        var activeRecord = await liveConfigurationStore.GetActiveWorldAsync(cancellationToken);
        if (activeRecord is not null && string.Equals(activeRecord.Slug, slug, StringComparison.Ordinal))
        {
            throw new InvalidOperationException("Activate a different world before deleting the active one.");
        }

        await repository.DeleteWorldAsync(slug, cancellationToken);
    }

    private static string EnsureUniqueSlug(string baseSlug, IEnumerable<string> existingSlugs)
    {
        var knownSlugs = new HashSet<string>(existingSlugs, StringComparer.Ordinal);
        if (!knownSlugs.Contains(baseSlug))
        {
            return baseSlug;
        }

        var index = 2;
        while (knownSlugs.Contains($"{baseSlug}-{index}"))
        {
            index++;
        }

        return $"{baseSlug}-{index}";
    }

    private static string NormalizeLineEndings(string text) => text.Replace("\r\n", "\n", StringComparison.Ordinal);
}

