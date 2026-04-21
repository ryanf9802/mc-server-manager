using McServerManager.Domain.Models;

namespace McServerManager.Application.Worlds;

public interface ILiveConfigurationStore
{
    Task<WorldFileSet> GetLiveFilesAsync(CancellationToken cancellationToken);
    Task ApplyLiveFilesAsync(WorldFileSet files, CancellationToken cancellationToken);
    Task<ActiveWorldRecord?> GetActiveWorldAsync(CancellationToken cancellationToken);
    Task SaveActiveWorldAsync(ActiveWorldRecord record, CancellationToken cancellationToken);
}

