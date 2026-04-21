using McServerManager.Desktop.Features.Worlds.ViewModels;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;

namespace McServerManager.Desktop.Features.Worlds.Views;

public sealed partial class WorldsWindow : Window
{
    private readonly WorldEditorViewModel _viewModel;

    public WorldsWindow(WorldEditorViewModel viewModel)
    {
        InitializeComponent();
        _viewModel = viewModel;
        DataContext = _viewModel;
        Activated += OnActivated;
    }

    private async void OnActivated(object sender, WindowActivatedEventArgs args)
    {
        Activated -= OnActivated;
        await _viewModel.InitializeAsync();
    }

    private async void OnWorldSelectionChanged(object sender, SelectionChangedEventArgs args)
    {
        if (((ListView)sender).SelectedItem is WorldListItemViewModel item)
        {
            await _viewModel.LoadWorldAsync(item.Slug);
        }
    }
}

