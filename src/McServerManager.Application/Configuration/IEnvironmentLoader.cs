namespace McServerManager.Application.Configuration;

public interface IEnvironmentLoader
{
    SftpSettings Load(string path);
}

