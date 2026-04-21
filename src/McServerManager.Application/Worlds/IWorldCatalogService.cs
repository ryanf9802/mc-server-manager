using McServerManager.Domain.Models;

namespace McServerManager.Application.Worlds;

public interface IWorldCatalogService
{
    Task<IReadOnlyList<WorldSummary>> GetWorldsAsync(CancellationToken cancellationToken);
    Task<WorldDetail?> GetWorldAsync(string slug, CancellationToken cancellationToken);
}

