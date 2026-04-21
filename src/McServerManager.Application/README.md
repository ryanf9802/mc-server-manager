# Application

## Purpose
Contains use-case orchestration, interfaces, and validation rules that coordinate domain types without owning transport details.

## Contents
- `Configuration/`: runtime settings contracts.
- `Worlds/`: list, load, create, save, and delete workflows.
- `Activation/`: activation workflow and hash coordination.
- `Validation/`: config file validation contracts and implementations.

## Dependency Rules
- Application code depends on Domain only.
- Infrastructure implements interfaces defined here.

## Change Notes
- Put orchestration here before adding logic to view-models or infrastructure adapters.

