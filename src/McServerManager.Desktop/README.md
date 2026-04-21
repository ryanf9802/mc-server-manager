# Desktop

## Purpose
Contains the Windows-only WinUI shell and world-management UI.

## Contents
- `AppHost/`: startup wiring and dependency injection.
- `Features/`: feature-oriented views and view-models.
- `Shared/`: cross-feature UI guidance and shared app concerns.
- `App.xaml` and `App.xaml.cs`: application entry point.

## Dependency Rules
- Desktop can depend on Application and Infrastructure, but feature logic should stay in view-models and services rather than code-behind.

## Change Notes
- Keep UI orchestration thin and push business rules down into application services.

