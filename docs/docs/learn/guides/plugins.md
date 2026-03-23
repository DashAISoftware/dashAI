---
title: "Module Guide: Plugins"
sidebar_label: Plugins
sidebar_position: 4
---

# Module Guide: Plugins

The plugin system lets you extend DashAI with new functionality without modifying the core platform. Plugins are distributed as PyPI packages and installed directly from the interface.

## What Plugins Can Add

A single plugin can contribute any combination of:

- **Models** — New classification, regression, or generation algorithms
- **Tasks** — New ML problem types
- **Data Loaders** — Support for new file formats
- **Converters** — New data transformation methods
- **Explainers** — New explainability methods
- **Metrics** — New evaluation metrics

## Installing Plugins

From the DashAI interface, navigate to the Plugins section. You can search for and install plugins published on PyPI. Once installed, new components appear automatically in their respective sections (models, converters, etc.).

## Developing Plugins

If you want to build your own plugins, see the [Build → Plugin Development](/build/plugin-development/overview) section for a complete guide covering plugin structure, development, and publishing to PyPI.

:::info
Plugins are discovered through Python's entry points mechanism. Any package that declares the correct entry point will be automatically recognized by DashAI's component registry.
:::
