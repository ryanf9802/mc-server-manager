using McServerManager.Application.Configuration;

namespace McServerManager.Infrastructure.Environment;

public sealed class DotEnvLoader : IEnvironmentLoader
{
    public SftpSettings Load(string path)
    {
        if (!File.Exists(path))
        {
            throw new FileNotFoundException($"Expected a .env file at '{path}'. Copy .env.example and fill in your SFTP settings.");
        }

        var values = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var rawLine in File.ReadAllLines(path))
        {
            var line = rawLine.Trim();
            if (string.IsNullOrWhiteSpace(line) || line.StartsWith("#", StringComparison.Ordinal))
            {
                continue;
            }

            var separatorIndex = line.IndexOf('=');
            if (separatorIndex <= 0)
            {
                continue;
            }

            var key = line[..separatorIndex].Trim();
            var value = line[(separatorIndex + 1)..].Trim().Trim('"');
            values[key] = value;
        }

        var missingKeys = RequiredKeys.Where(key => !values.TryGetValue(key, out var value) || string.IsNullOrWhiteSpace(value)).ToArray();
        if (missingKeys.Length > 0)
        {
            throw new InvalidOperationException($"The .env file is missing required keys: {string.Join(", ", missingKeys)}");
        }

        if (!int.TryParse(values["SFTP_PORT"], out var port))
        {
            throw new InvalidOperationException("SFTP_PORT must be a valid integer.");
        }

        return new SftpSettings(
            values["SFTP_HOST"],
            port,
            values["SFTP_USERNAME"],
            values["SFTP_PASSWORD"],
            values["SFTP_SERVER_ROOT"]);
    }

    private static readonly string[] RequiredKeys =
    [
        "SFTP_HOST",
        "SFTP_PORT",
        "SFTP_USERNAME",
        "SFTP_PASSWORD",
        "SFTP_SERVER_ROOT",
    ];
}
