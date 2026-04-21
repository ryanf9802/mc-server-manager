using McServerManager.Application.Configuration;
using Renci.SshNet;

namespace McServerManager.Infrastructure.Sftp;

public sealed class SftpConnectionFactory(SftpSettings settings)
{
    public SftpClient CreateConnectedClient()
    {
        var authenticationMethod = new PasswordAuthenticationMethod(settings.Username, settings.Password);
        var connectionInfo = new ConnectionInfo(settings.Host, settings.Port, settings.Username, authenticationMethod);
        var client = new SftpClient(connectionInfo);
        client.Connect();
        return client;
    }
}

