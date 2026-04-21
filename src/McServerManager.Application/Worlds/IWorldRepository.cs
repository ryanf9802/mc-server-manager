using McServerManager.Domain.Models;

namespace McServerManager.Application.Worlds;

public interface IWorldRepository
{
    Task<IReadOnlyList<WorldManifest>> ListWorldsAsync(CancellationToken cancellationToken);
    Task<WorldFileSet?> GetFilesAsync(string slug, CancellationToken cancellationToken);
    Task SaveWorldAsync(WorldManifest manifest, WorldFileSet files, CancellationToken cancellationToken);
    Task DeleteWorldAsync(string slug, CancellationToken cancellationToken);
}

