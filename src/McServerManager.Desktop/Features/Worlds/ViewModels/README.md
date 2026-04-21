# World ViewModels

## Purpose
Keeps presentation state, command handling, and editor workflows separate from the XAML shell.

## Contents
- `WorldEditorViewModel.cs`: list state, raw text editing, save/apply/revert logic, and status messaging.

## Dependency Rules
- View-models may talk to application services only.

## Change Notes
- Add new view-model files here when the feature grows beyond a single shell.

