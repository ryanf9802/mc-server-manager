# Activation

## Purpose
Coordinates the explicit apply step that replaces the live remote config pair.

## Contents
- `IActivationService.cs`: activation contract.
- `IHashService.cs`: hash abstraction used for drift checks.
- `WorldActivationService.cs`: apply workflow and active-pointer persistence.

## Dependency Rules
- Activation logic depends on world storage interfaces, not transport details.

## Change Notes
- Keep drift and active-pointer rules centralized here.

