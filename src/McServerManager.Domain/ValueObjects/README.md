# Domain Value Objects

## Purpose
Holds small reusable value objects and enums that describe validation and status state.

## Contents
- `WorldStatus.cs`: UI-facing status buckets.
- `ValidationIssue.cs`: one validation problem.
- `ValidationResult.cs`: aggregate validation output.

## Dependency Rules
- Keep these types serialization-friendly and side-effect free.

## Change Notes
- Expand here before inventing ad hoc tuples or dictionaries in higher layers.

