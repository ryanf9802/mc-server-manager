using McServerManager.Desktop.AppHost;
using McServerManager.Desktop.Features.Worlds.Views;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.UI.Xaml;

namespace McServerManager.Desktop;

public partial class App : Application
{
    private Window? _window;

    public App()
    {
        InitializeComponent();
    }

    protected override void OnLaunched(LaunchActivatedEventArgs args)
    {
        var services = Bootstrapper.CreateServiceProvider();
        _window = services.GetRequiredService<WorldsWindow>();
        _window.Activate();
    }
}
