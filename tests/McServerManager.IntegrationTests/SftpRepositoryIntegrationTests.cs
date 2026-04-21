using McServerManager.Infrastructure.Environment;

namespace McServerManager.IntegrationTests;

public sealed class SftpRepositoryIntegrationTests
{
    [Fact]
    public void DotEnvLoader_LoadsSettingsFromProvidedPath()
    {
        var tempPath = Path.GetTempFileName();
        try
        {
            File.WriteAllText(
                tempPath,
                """
                SFTP_HOST=example.org
                SFTP_PORT=22
                SFTP_USERNAME=tester
                SFTP_PASSWORD=secret
                SFTP_SERVER_ROOT=/minecraft
                """);

            var loader = new DotEnvLoader();
            var settings = loader.Load(tempPath);

            Assert.Equal("example.org", settings.Host);
            Assert.Equal(22, settings.Port);
            Assert.Equal("/minecraft", settings.ServerRoot);
        }
        finally
        {
            File.Delete(tempPath);
        }
    }

    [Fact]
    public void LiveSftpSmokeTest_IsOptIn()
    {
        var envPath = Environment.GetEnvironmentVariable("MC_SERVER_MANAGER_INTEGRATION_ENV");
        if (string.IsNullOrWhiteSpace(envPath))
        {
            return;
        }

        Assert.True(File.Exists(envPath), $"Expected integration env file at '{envPath}'.");
    }
}
