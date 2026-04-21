namespace McServerManager.Application.Activation;

public interface IActivationService
{
    Task ActivateWorldAsync(string slug, CancellationToken cancellationToken);
}

