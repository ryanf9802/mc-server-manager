using System.Text;
using System.Text.Json;
using McServerManager.Application.Worlds;
using McServerManager.Domain.Models;
using McServerManager.Infrastructure.Sftp;
using Renci.SshNet;

namespace McServerManager.Infrastructure.Storage;

public sealed class SftpLiveConfigurationStore(
    SftpConnectionFactory connectionFactory,
    RemotePathBuilder pathBuilder) : ILiveConfigurationStore
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web)
    {
        WriteIndented = true,
    };

    public Task<WorldFileSet> GetLiveFilesAsync(CancellationToken cancellationToken)
    {
        return Task.Run(() =>
        {
            cancellationToken.ThrowIfCancellationRequested();
            using var client = connectionFactory.CreateConnectedClient();

            var serverProperties = client.Exists(pathBuilder.LiveServerPropertiesPath)
                ? ReadAllText(client, pathBuilder.LiveServerPropertiesPath)
                : string.Empty;

            var whitelist = client.Exists(pathBuilder.LiveWhitelistPath)
                ? ReadAllText(client, pathBuilder.LiveWhitelistPath)
                : "[]";

            return new WorldFileSet(serverProperties, whitelist);
        }, cancellationToken);
    }

    public Task ApplyLiveFilesAsync(WorldFileSet files, CancellationToken cancellationToken)
    {
        return Task.Run(() =>
        {
            cancellationToken.ThrowIfCancellationRequested();
            using var client = connectionFactory.CreateConnectedClient();

            EnsureDirectory(client, pathBuilder.ManagementRoot);
            WriteAllText(client, pathBuilder.LiveServerPropertiesPath, files.ServerPropertiesText);
            WriteAllText(client, pathBuilder.LiveWhitelistPath, files.WhitelistJsonText);
        }, cancellationToken);
    }

    public Task<ActiveWorldRecord?> GetActiveWorldAsync(CancellationToken cancellationToken)
    {
        return Task.Run<ActiveWorldRecord?>(() =>
        {
            cancellationToken.ThrowIfCancellationRequested();
            using var client = connectionFactory.CreateConnectedClient();
            if (!client.Exists(pathBuilder.ActiveWorldPath))
            {
                return null;
            }

            var json = ReadAllText(client, pathBuilder.ActiveWorldPath);
            return JsonSerializer.Deserialize<ActiveWorldRecord>(json, JsonOptions);
        }, cancellationToken);
    }

    public Task SaveActiveWorldAsync(ActiveWorldRecord record, CancellationToken cancellationToken)
    {
        return Task.Run(() =>
        {
            cancellationToken.ThrowIfCancellationRequested();
            using var client = connectionFactory.CreateConnectedClient();
            EnsureDirectory(client, pathBuilder.ManagementRoot);
            WriteAllText(client, pathBuilder.ActiveWorldPath, JsonSerializer.Serialize(record, JsonOptions));
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
}

