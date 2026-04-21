using McServerManager.Domain.Models;

namespace McServerManager.Application.Worlds;

public interface IWorldEditorService
{
    Task<WorldDetail> CreateDraftFromLiveAsync(string displayName, CancellationToken cancellationToken);
    Task SaveWorldAsync(WorldDetail detail, CancellationToken cancellationToken);
    Task DeleteWorldAsync(string slug, CancellationToken cancellationToken);
}

