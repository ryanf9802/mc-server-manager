using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using McServerManager.Application.Activation;
using McServerManager.Application.Worlds;
using McServerManager.Domain.Models;
using McServerManager.Domain.ValueObjects;

namespace McServerManager.Desktop.Features.Worlds.ViewModels;

public sealed class WorldEditorViewModel : ObservableObject
{
    private readonly IWorldCatalogService _catalogService;
    private readonly IWorldEditorService _editorService;
    private readonly IActivationService _activationService;

    private WorldManifest? _currentManifest;
    private WorldStatus _currentStatus;
    private string _originalServerPropertiesText = string.Empty;
    private string _originalWhitelistJsonText = "[]";
    private bool _initialized;

    private string _newWorldName = string.Empty;
    private string _currentDisplayName = string.Empty;
    private string _serverPropertiesText = string.Empty;
    private string _whitelistJsonText = "[]";
    private string _statusMessage = "Load a world or create a draft to begin.";
    private WorldListItemViewModel? _selectedWorldItem;
    private bool _hasPersistedWorld;

    public WorldEditorViewModel(
        IWorldCatalogService catalogService,
        IWorldEditorService editorService,
        IActivationService activationService)
    {
        _catalogService = catalogService;
        _editorService = editorService;
        _activationService = activationService;

        RefreshCommand = new AsyncRelayCommand(RefreshAsync);
        CreateDraftCommand = new AsyncRelayCommand(CreateDraftAsync, () => !string.IsNullOrWhiteSpace(NewWorldName));
        SaveCommand = new AsyncRelayCommand(SaveAsync, () => HasDraftLoaded);
        ActivateCommand = new AsyncRelayCommand(ActivateAsync, () => HasDraftLoaded);
        DeleteCommand = new AsyncRelayCommand(DeleteAsync, () => HasDraftLoaded);
        RevertCommand = new AsyncRelayCommand(RevertAsync, () => HasDraftLoaded);
    }

    public ObservableCollection<WorldListItemViewModel> Worlds { get; } = [];

    public IAsyncRelayCommand RefreshCommand { get; }
    public IAsyncRelayCommand CreateDraftCommand { get; }
    public IAsyncRelayCommand SaveCommand { get; }
    public IAsyncRelayCommand ActivateCommand { get; }
    public IAsyncRelayCommand DeleteCommand { get; }
    public IAsyncRelayCommand RevertCommand { get; }

    public string NewWorldName
    {
        get => _newWorldName;
        set
        {
            if (SetProperty(ref _newWorldName, value))
            {
                CreateDraftCommand.NotifyCanExecuteChanged();
            }
        }
    }

    public string CurrentDisplayName
    {
        get => _currentDisplayName;
        set
        {
            if (SetProperty(ref _currentDisplayName, value))
            {
                OnPropertyChanged(nameof(DirtyLabel));
            }
        }
    }

    public string ServerPropertiesText
    {
        get => _serverPropertiesText;
        set
        {
            if (SetProperty(ref _serverPropertiesText, value))
            {
                OnPropertyChanged(nameof(DirtyLabel));
            }
        }
    }

    public string WhitelistJsonText
    {
        get => _whitelistJsonText;
        set
        {
            if (SetProperty(ref _whitelistJsonText, value))
            {
                OnPropertyChanged(nameof(DirtyLabel));
            }
        }
    }

    public string StatusMessage
    {
        get => _statusMessage;
        private set => SetProperty(ref _statusMessage, value);
    }

    public WorldListItemViewModel? SelectedWorldItem
    {
        get => _selectedWorldItem;
        set => SetProperty(ref _selectedWorldItem, value);
    }

    public string CurrentStatusLabel => HasDraftLoaded ? $"Status: {_currentStatus.ToFriendlyLabel()}" : "Status: No world selected";

    public string CurrentSlugLabel => _currentManifest is null ? string.Empty : $"Slug: {_currentManifest.Slug}";

    public string DirtyLabel => IsDirty ? "Unsaved changes" : "Saved state loaded";

    private bool HasDraftLoaded => _currentManifest is not null;

    private bool IsDirty =>
        _currentManifest is not null &&
        (!string.Equals(CurrentDisplayName, _currentManifest.DisplayName, StringComparison.Ordinal) ||
         !string.Equals(ServerPropertiesText, _originalServerPropertiesText, StringComparison.Ordinal) ||
         !string.Equals(WhitelistJsonText, _originalWhitelistJsonText, StringComparison.Ordinal));

    public async Task InitializeAsync()
    {
        if (_initialized)
        {
            return;
        }

        _initialized = true;
        await RefreshAsync();
    }

    public async Task LoadWorldAsync(string slug)
    {
        try
        {
            var detail = await _catalogService.GetWorldAsync(slug, CancellationToken.None);
            if (detail is null)
            {
                StatusMessage = $"World '{slug}' no longer exists on the remote host.";
                return;
            }

            ApplyDetail(detail);
            StatusMessage = $"Loaded '{detail.Manifest.DisplayName}' from the remote world store.";
        }
        catch (Exception exception)
        {
            StatusMessage = exception.Message;
        }
    }

    private async Task RefreshAsync()
    {
        try
        {
            var worlds = await _catalogService.GetWorldsAsync(CancellationToken.None);
            Worlds.Clear();
            foreach (var world in worlds)
            {
                Worlds.Add(new WorldListItemViewModel(world.Manifest.Slug, world.Manifest.DisplayName, world.Status));
            }

            if (_currentManifest is not null && _hasPersistedWorld)
            {
                var refreshedDetail = await _catalogService.GetWorldAsync(_currentManifest.Slug, CancellationToken.None);
                if (refreshedDetail is not null)
                {
                    ApplyDetail(refreshedDetail);
                    SelectedWorldItem = Worlds.FirstOrDefault(item => item.Slug == refreshedDetail.Manifest.Slug);
                }
                else
                {
                    ClearEditor();
                }
            }

            StatusMessage = worlds.Count == 0
                ? "No managed worlds found yet. Create a draft from the live files to start."
                : $"Loaded {worlds.Count} managed world(s).";
        }
        catch (Exception exception)
        {
            StatusMessage = exception.Message;
        }
    }

    private async Task CreateDraftAsync()
    {
        try
        {
            var detail = await _editorService.CreateDraftFromLiveAsync(NewWorldName, CancellationToken.None);
            ApplyDetail(detail);
            _hasPersistedWorld = false;
            SelectedWorldItem = null;
            StatusMessage = $"Drafted '{detail.Manifest.DisplayName}' from the current live remote files. Save to persist it.";
        }
        catch (Exception exception)
        {
            StatusMessage = exception.Message;
        }
    }

    private async Task SaveAsync()
    {
        if (_currentManifest is null)
        {
            return;
        }

        try
        {
            var detail = new WorldDetail(
                _currentManifest with { DisplayName = CurrentDisplayName },
                new WorldFileSet(ServerPropertiesText, WhitelistJsonText),
                _currentStatus);

            await _editorService.SaveWorldAsync(detail, CancellationToken.None);
            _hasPersistedWorld = true;
            await RefreshAsync();
            await LoadWorldAsync(_currentManifest.Slug);
            StatusMessage = $"Saved '{CurrentDisplayName}' to the managed remote world store.";
        }
        catch (Exception exception)
        {
            StatusMessage = exception.Message;
        }
    }

    private async Task ActivateAsync()
    {
        if (_currentManifest is null)
        {
            return;
        }

        try
        {
            if (IsDirty)
            {
                await SaveAsync();
            }

            await _activationService.ActivateWorldAsync(_currentManifest.Slug, CancellationToken.None);
            await RefreshAsync();
            await LoadWorldAsync(_currentManifest.Slug);
            StatusMessage = $"Activated '{CurrentDisplayName}'. Live remote files now match this world.";
        }
        catch (Exception exception)
        {
            StatusMessage = exception.Message;
        }
    }

    private async Task DeleteAsync()
    {
        if (_currentManifest is null)
        {
            return;
        }

        try
        {
            if (!_hasPersistedWorld)
            {
                ClearEditor();
                StatusMessage = "Discarded the unsaved draft.";
                return;
            }

            await _editorService.DeleteWorldAsync(_currentManifest.Slug, CancellationToken.None);
            ClearEditor();
            await RefreshAsync();
            StatusMessage = "Deleted the selected managed world.";
        }
        catch (Exception exception)
        {
            StatusMessage = exception.Message;
        }
    }

    private async Task RevertAsync()
    {
        if (_currentManifest is null)
        {
            ClearEditor();
            StatusMessage = "Draft cleared.";
            return;
        }

        if (!_hasPersistedWorld)
        {
            ClearEditor();
            StatusMessage = "Discarded the unsaved draft.";
            return;
        }

        await LoadWorldAsync(_currentManifest.Slug);
    }

    private void ApplyDetail(WorldDetail detail)
    {
        _currentManifest = detail.Manifest;
        _currentStatus = detail.Status;
        _hasPersistedWorld = true;
        CurrentDisplayName = detail.Manifest.DisplayName;
        ServerPropertiesText = detail.Files.ServerPropertiesText;
        WhitelistJsonText = detail.Files.WhitelistJsonText;
        _originalServerPropertiesText = detail.Files.ServerPropertiesText;
        _originalWhitelistJsonText = detail.Files.WhitelistJsonText;
        OnPropertyChanged(nameof(CurrentStatusLabel));
        OnPropertyChanged(nameof(CurrentSlugLabel));
        OnPropertyChanged(nameof(DirtyLabel));
        NotifyCommandStateChanged();
    }

    private void ClearEditor()
    {
        _currentManifest = null;
        _currentStatus = WorldStatus.Inactive;
        _hasPersistedWorld = false;
        CurrentDisplayName = string.Empty;
        ServerPropertiesText = string.Empty;
        WhitelistJsonText = "[]";
        _originalServerPropertiesText = string.Empty;
        _originalWhitelistJsonText = "[]";
        SelectedWorldItem = null;
        OnPropertyChanged(nameof(CurrentStatusLabel));
        OnPropertyChanged(nameof(CurrentSlugLabel));
        OnPropertyChanged(nameof(DirtyLabel));
        NotifyCommandStateChanged();
    }

    private void NotifyCommandStateChanged()
    {
        SaveCommand.NotifyCanExecuteChanged();
        ActivateCommand.NotifyCanExecuteChanged();
        DeleteCommand.NotifyCanExecuteChanged();
        RevertCommand.NotifyCanExecuteChanged();
        CreateDraftCommand.NotifyCanExecuteChanged();
    }
}

public sealed class WorldListItemViewModel(string slug, string displayName, WorldStatus status)
{
    public string Slug { get; } = slug;
    public string DisplayName { get; } = displayName;
    public WorldStatus Status { get; } = status;
    public string StatusLabel { get; } = status.ToFriendlyLabel();
}

internal static class WorldStatusExtensions
{
    public static string ToFriendlyLabel(this WorldStatus status)
    {
        return status switch
        {
            WorldStatus.Active => "Active",
            WorldStatus.PendingApply => "Pending Apply",
            WorldStatus.UnmanagedLive => "Unmanaged Live",
            _ => "Inactive",
        };
    }
}
