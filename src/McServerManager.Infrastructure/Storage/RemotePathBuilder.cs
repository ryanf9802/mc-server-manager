using McServerManager.Application.Configuration;

namespace McServerManager.Infrastructure.Storage;

public sealed class RemotePathBuilder(SftpSettings settings)
{
    private string ServerRoot => settings.NormalizedServerRoot;

    public string ManagementRoot => Combine(ServerRoot, ".mc-manager");
    public string WorldsRoot => Combine(ManagementRoot, "worlds");
    public string ActiveWorldPath => Combine(ManagementRoot, "active-world.json");
    public string LiveServerPropertiesPath => Combine(ServerRoot, "server.properties");
    public string LiveWhitelistPath => Combine(ServerRoot, "whitelist.json");

    public string WorldRoot(string slug) => Combine(WorldsRoot, slug);
    public string WorldManifestPath(string slug) => Combine(WorldRoot(slug), "world.json");
    public string WorldServerPropertiesPath(string slug) => Combine(WorldRoot(slug), "server.properties");
    public string WorldWhitelistPath(string slug) => Combine(WorldRoot(slug), "whitelist.json");

    public static string Combine(params string[] segments)
    {
        var firstSegment = segments.FirstOrDefault(segment => !string.IsNullOrWhiteSpace(segment)) ?? string.Empty;
        var isRooted = firstSegment.StartsWith('/', StringComparison.Ordinal);
        var combined = string.Join("/", segments
            .Where(segment => !string.IsNullOrWhiteSpace(segment))
            .Select(segment => segment.Trim('/')));

        return isRooted ? $"/{combined}" : combined;
    }
}
