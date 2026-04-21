using McServerManager.Application.Activation;
using McServerManager.Application.Configuration;
using McServerManager.Application.Validation;
using McServerManager.Application.Worlds;
using McServerManager.Desktop.Features.Worlds.ViewModels;
using McServerManager.Desktop.Features.Worlds.Views;
using McServerManager.Infrastructure.Environment;
using McServerManager.Infrastructure.Hashing;
using McServerManager.Infrastructure.Sftp;
using McServerManager.Infrastructure.Storage;
using Microsoft.Extensions.DependencyInjection;

namespace McServerManager.Desktop.AppHost;

public static class Bootstrapper
{
    public static IServiceProvider CreateServiceProvider()
    {
        var services = new ServiceCollection();

        services.AddSingleton<IEnvironmentLoader, DotEnvLoader>();
        services.AddSingleton(provider =>
        {
            var envLoader = provider.GetRequiredService<IEnvironmentLoader>();
            var envPath = Path.Combine(AppContext.BaseDirectory, ".env");
            return envLoader.Load(envPath);
        });

        services.AddSingleton<SftpConnectionFactory>();
        services.AddSingleton<RemotePathBuilder>();
        services.AddSingleton<IWorldRepository, SftpWorldRepository>();
        services.AddSingleton<ILiveConfigurationStore, SftpLiveConfigurationStore>();
        services.AddSingleton<IHashService, Sha256HashService>();
        services.AddSingleton<IServerPropertiesValidator, ServerPropertiesValidator>();
        services.AddSingleton<IWhitelistValidator, WhitelistValidator>();
        services.AddSingleton<IWorldCatalogService, WorldCatalogService>();
        services.AddSingleton<IWorldEditorService, WorldEditorService>();
        services.AddSingleton<IActivationService, WorldActivationService>();

        services.AddTransient<WorldEditorViewModel>();
        services.AddTransient<WorldsWindow>();

        return services.BuildServiceProvider();
    }
}

