# Workflows

## Purpose

Documents the GitHub Actions workflows that build, validate, and publish this project.

## Contents

- `release-windows.yml`: builds Windows release artifacts on pushes to `main` and publishes a GitHub Release.

## Dependency Rules

- Workflows should invoke the same repo entrypoints developers use locally whenever possible.

## Change Notes

- Update this README when workflow triggers, published assets, or release behavior change.
