using McServerManager.Application.Activation;
using McServerManager.Application.Worlds;
using McServerManager.Domain.Models;
using McServerManager.Domain.ValueObjects;

namespace McServerManager.UnitTests;

public sealed class WorldCatalogServiceTests
{
    [Fact]
    public async Task GetWorldsAsync_MarksMatchingWorldActive()
    {
        var files = new WorldFileSet("motd=Weekend", "[]");
        var hashService = new FakeHashService();
        var activeRecord = new ActiveWorldRecord(
            "weekend",
            DateTimeOffset.UtcNow,
            hashService.ComputeSha256(files.ServerPropertiesText),
            hashService.ComputeSha256(files.WhitelistJsonText));

        var service = new WorldCatalogService(
            new FakeWorldRepository(
            [
                new WorldManifest("weekend", "Weekend", DateTimeOffset.UtcNow, DateTimeOffset.UtcNow)
            ],
            new Dictionary<string, WorldFileSet> { ["weekend"] = files }),
            new FakeLiveConfigurationStore(files, activeRecord),
            hashService);

        var worlds = await service.GetWorldsAsync(CancellationToken.None);

        Assert.Single(worlds);
        Assert.Equal(WorldStatus.Active, worlds[0].Status);
    }

    [Fact]
    public async Task GetWorldsAsync_MarksPointerWorldUnmanagedWhenLiveFilesDrift()
    {
        var managedFiles = new WorldFileSet("motd=Weekend", "[]");
        var liveFiles = new WorldFileSet("motd=Drifted", "[]");
        var hashService = new FakeHashService();
        var activeRecord = new ActiveWorldRecord(
            "weekend",
            DateTimeOffset.UtcNow,
            hashService.ComputeSha256(managedFiles.ServerPropertiesText),
            hashService.ComputeSha256(managedFiles.WhitelistJsonText));

        var service = new WorldCatalogService(
            new FakeWorldRepository(
            [
                new WorldManifest("weekend", "Weekend", DateTimeOffset.UtcNow, DateTimeOffset.UtcNow)
            ],
            new Dictionary<string, WorldFileSet> { ["weekend"] = managedFiles }),
            new FakeLiveConfigurationStore(liveFiles, activeRecord),
            hashService);

        var worlds = await service.GetWorldsAsync(CancellationToken.None);

        Assert.Single(worlds);
        Assert.Equal(WorldStatus.UnmanagedLive, worlds[0].Status);
    }

    private sealed class FakeWorldRepository(
        IReadOnlyList<WorldManifest> manifests,
        IReadOnlyDictionary<string, WorldFileSet> files) : IWorldRepository
    {
        public Task<IReadOnlyList<WorldManifest>> ListWorldsAsync(CancellationToken cancellationToken) => Task.FromResult(manifests);

        public Task<WorldFileSet?> GetFilesAsync(string slug, CancellationToken cancellationToken)
        {
            files.TryGetValue(slug, out var value);
            return Task.FromResult(value);
        }

        public Task SaveWorldAsync(WorldManifest manifest, WorldFileSet worldFiles, CancellationToken cancellationToken) => Task.CompletedTask;

        public Task DeleteWorldAsync(string slug, CancellationToken cancellationToken) => Task.CompletedTask;
    }

    private sealed class FakeLiveConfigurationStore(WorldFileSet liveFiles, ActiveWorldRecord? activeRecord) : ILiveConfigurationStore
    {
        public Task<WorldFileSet> GetLiveFilesAsync(CancellationToken cancellationToken) => Task.FromResult(liveFiles);

        public Task ApplyLiveFilesAsync(WorldFileSet files, CancellationToken cancellationToken) => Task.CompletedTask;

        public Task<ActiveWorldRecord?> GetActiveWorldAsync(CancellationToken cancellationToken) => Task.FromResult(activeRecord);

        public Task SaveActiveWorldAsync(ActiveWorldRecord record, CancellationToken cancellationToken) => Task.CompletedTask;
    }

    private sealed class FakeHashService : IHashService
    {
        public string ComputeSha256(string content) => $"hash::{content}";
    }
}

