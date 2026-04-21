namespace McServerManager.Application.Configuration;

public sealed record SftpSettings(
    string Host,
    int Port,
    string Username,
    string Password,
    string ServerRoot)
{
    public string NormalizedServerRoot => ServerRoot.Trim().TrimEnd('/');
}

