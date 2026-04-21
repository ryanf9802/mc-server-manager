namespace McServerManager.Application.Activation;

public interface IHashService
{
    string ComputeSha256(string content);
}

