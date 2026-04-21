using McServerManager.Application.Worlds;
using McServerManager.Domain.Models;

namespace McServerManager.Application.Activation;

public sealed class WorldActivationService(
    IWorldRepository repository,
    ILiveConfigurationStore liveConfigurationStore,
    IHashService hashService) : IActivationService
{
    public async Task ActivateWorldAsync(string slug, CancellationToken cancellationToken)
    {
        var files = await repository.GetFilesAsync(slug, cancellationToken);
        if (files is null)
        {
            throw new InvalidOperationException($"World '{slug}' was not found.");
        }

        await liveConfigurationStore.ApplyLiveFilesAsync(files, cancellationToken);

        var activeRecord = new ActiveWorldRecord(
            slug,
            DateTimeOffset.UtcNow,
            hashService.ComputeSha256(files.ServerPropertiesText),
            hashService.ComputeSha256(files.WhitelistJsonText));

        await liveConfigurationStore.SaveActiveWorldAsync(activeRecord, cancellationToken);
    }
}

