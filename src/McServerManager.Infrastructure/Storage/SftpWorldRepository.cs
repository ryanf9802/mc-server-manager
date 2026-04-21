using System.Text;
using System.Text.Json;
using McServerManager.Application.Worlds;
using McServerManager.Domain.Models;
using McServerManager.Infrastructure.Sftp;
using Renci.SshNet;

namespace McServerManager.Infrastructure.Storage;

public sealed class SftpWorldRepository(
    SftpConnectionFactory connectionFactory,
    RemotePathBuilder pathBuilder) : IWorldRepository
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web)
    {
        WriteIndented = true,
    };

    public Task<IReadOnlyList<WorldManifest>> ListWorldsAsync(CancellationToken cancellationToken)
    {
        return Task.Run<IReadOnlyList<WorldManifest>>(() =>
        {
            cancellationToken.ThrowIfCancellationRequested();
            using var client = connectionFactory.CreateConnectedClient();

            if (!client.Exists(pathBuilder.WorldsRoot))
            {
                return [];
            }

            var manifests = new List<WorldManifest>();
            foreach (var entry in client.ListDirectory(pathBuilder.WorldsRoot))
            {
                cancellationToken.ThrowIfCancellationRequested();
                if (!entry.IsDirectory || entry.Name is "." or "..")
                {
                    continue;
                }

                var manifestPath = pathBuilder.WorldManifestPath(entry.Name);
                if (!client.Exists(manifestPath))
                {
                    continue;
                }

                var manifestJson = ReadAllText(client, manifestPath);
                var manifest = JsonSerializer.Deserialize<WorldManifest>(manifestJson, JsonOptions);
                if (manifest is not null)
                {
                    manifests.Add(manifest);
                }
            }

            return manifests;
        }, cancellationToken);
    }

    public Task<WorldFileSet?> GetFilesAsync(string slug, CancellationToken cancellationToken)
    {
        return Task.Run<WorldFileSet?>(() =>
        {
            cancellationToken.ThrowIfCancellationRequested();
            using var client = connectionFactory.CreateConnectedClient();

            var serverPropertiesPath = pathBuilder.WorldServerPropertiesPath(slug);
            var whitelistPath = pathBuilder.WorldWhitelistPath(slug);
            if (!client.Exists(serverPropertiesPath) || !client.Exists(whitelistPath))
            {
                return null;
            }

            return new WorldFileSet(
                ReadAllText(client, serverPropertiesPath),
                ReadAllText(client, whitelistPath));
        }, cancellationToken);
    }

    public Task SaveWorldAsync(WorldManifest manifest, WorldFileSet files, CancellationToken cancellationToken)
    {
        return Task.Run(() =>
        {
            cancellationToken.ThrowIfCancellationRequested();
            using var client = connectionFactory.CreateConnectedClient();

            EnsureDirectory(client, pathBuilder.WorldsRoot);
            EnsureDirectory(client, pathBuilder.WorldRoot(manifest.Slug));

            WriteAllText(client, pathBuilder.WorldManifestPath(manifest.Slug), JsonSerializer.Serialize(manifest, JsonOptions));
            WriteAllText(client, pathBuilder.WorldServerPropertiesPath(manifest.Slug), files.ServerPropertiesText);
            WriteAllText(client, pathBuilder.WorldWhitelistPath(manifest.Slug), files.WhitelistJsonText);
        }, cancellationToken);
    }

    public Task DeleteWorldAsync(string slug, CancellationToken cancellationToken)
    {
        return Task.Run(() =>
        {
            cancellationToken.ThrowIfCancellationRequested();
            using var client = connectionFactory.CreateConnectedClient();

            var root = pathBuilder.WorldRoot(slug);
            if (!client.Exists(root))
            {
                return;
            }

            DeleteDirectoryRecursive(client, root, cancellationToken);
        }, cancellationToken);
    }

    private static void EnsureDirectory(SftpClient client, string path)
    {
        var segments = path.Split('/', StringSplitOptions.RemoveEmptyEntries);
        var current = path.StartsWith('/') ? "/" : string.Empty;

        foreach (var segment in segments)
        {
            current = string.IsNullOrEmpty(current) || current == "/" ? $"{current}{segment}" : $"{current}/{segment}";
            if (!client.Exists(current))
            {
                client.CreateDirectory(current);
            }
        }
    }

    private static string ReadAllText(SftpClient client, string path)
    {
        using var stream = client.OpenRead(path);
        using var reader = new StreamReader(stream, Encoding.UTF8, true);
        return reader.ReadToEnd();
    }

    private static void WriteAllText(SftpClient client, string path, string content)
    {
        using var stream = client.Open(path, FileMode.Create, FileAccess.Write);
        using var writer = new StreamWriter(stream, new UTF8Encoding(false));
        writer.Write(content);
        writer.Flush();
    }

    private static void DeleteDirectoryRecursive(SftpClient client, string path, CancellationToken cancellationToken)
    {
        foreach (var entry in client.ListDirectory(path))
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (entry.Name is "." or "..")
            {
                continue;
            }

            if (entry.IsDirectory)
            {
                DeleteDirectoryRecursive(client, entry.FullName, cancellationToken);
            }
            else
            {
                client.DeleteFile(entry.FullName);
            }
        }

        client.DeleteDirectory(path);
    }
}

