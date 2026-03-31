---
title: Interface Tour
sidebar_label: Interface Tour
sidebar_position: 3
---

# Interface Tour

This page describes the main areas of the DashAI interface and what each one does.

---

## Navigation Bar

The top bar is always visible and provides access to all main modules:

| Section        | What it does                                                         |
| -------------- | -------------------------------------------------------------------- |
| **DATASETS**   | Load datasets, explore their content, and open notebooks             |
| **MODELS**     | Create sessions, train models, compare results, generate predictions |
| **GENERATIVE** | Interact with text and image generation models                       |
| **PLUGINS**    | Install and manage plugins                                           |

The globe icon (🌐) switches the interface language. The gear icon (⚙️) opens platform settings. The question mark icon (?) opens contextual help.

---

## Left Sidebar

The sidebar content changes depending on which module you are in.

**In Datasets:** Shows **Available Datasets** (with row and column counts) and **Notebooks** (grouped under their parent dataset). A search bar filters both. The **New Dataset/Notebook** button at the top starts the upload or notebook creation flow.

**In Models:** Shows **Available Datasets** and **Sessions** grouped by task type. A search bar filters datasets and sessions. The **New Session** button creates a new session.

**In Generative:** Shows sessions organized by generative task type.

---

## Main Area

The central content area changes based on what you have selected.

### Datasets — Dataset View

When you click a dataset in the sidebar, the main area shows the dataset's EDA panel:

- **Header** — dataset name, creation date, Quality Score, and NEW NOTEBOOK button
- **Summary cards** — Total Rows, Total Columns, File Size, Duplicated Rows, Missing Values
- **Quality banner** — green checkmark if no issues, warning if issues were detected
- **Analysis tabs** — Overview, Numerical Analysis, Categorical, Text, Data Quality, Correlations

### Datasets — Notebook View

When a notebook is open:

- **Notebook title** — `Notebook: [Dataset Name] Preview`
- **Toolbar** — FILTERS and EXPORT controls
- **Dataset preview table** — paginated view of the data in its current state; updates after each converter
- **Operation timeline** — each Explorer or Converter you add appears below the preview as a block with its result, status badge, and edit/delete controls
- **SAVE AS NEW DATASET** button — top right, saves the current state as a new dataset

### Models — Session View

When a session is open:

- **Model Comparison panel** — table of all models with their metrics; toggle between TRAINING, VALIDATION, and TEST splits; switch between TABLE and CHARTS views
- **Model cards** — one per model, expandable, each with EDIT, TRAIN/RE-TRAIN buttons, a status badge, and four inner tabs: LIVE METRICS, EXPLAINABILITY, PREDICTIONS, HYPERPARAMETERS

---

## Right Panel

The right panel is context-sensitive and appears alongside the main area.

**In Notebooks (EXPLORE tab):** The Analysis Tools panel lists all available explorer tools organized by category. Hover over any tool to see a preview image and description. Click to open the configuration modal.

**In Notebooks (CONVERT tab):** Same panel, but showing converter tools organized by category.

**In Models:** The Available Models panel lists all models compatible with the current session's task. Hover for a description. Click to open the Add Model modal.

**In Generative:** Lists available generative models. Hover for a description.

---

## Configuration Modals

Many tools open a two-step configuration modal:

**Step 1 — Configure Scope:** Select which columns the tool will use. The column selector table shows index, name, value type, and data type. A counter at the top shows how many columns are selected and how many are required.

For converters, Step 1 also includes **row scope** — select rows by range, by specific indices, or use SELECT ALL.

**Step 2 — Configure Parameters:** Each tool has its own set of parameters, auto-generated from the tool's schema. Each parameter has a **?** help icon. Click **CREATE EXPLORER** or **CREATE CONVERTER** to apply.

---

## Job Queue

The Job Queue is visible at the bottom right of the screen whenever jobs are running or have recently completed. It shows:

- Active jobs (with a spinner and count)
- Failed jobs (with a red indicator and count)
- A **Show Completed** button to review finished jobs

Long-running operations — training, exploration, prediction generation — all run as background jobs so you can continue working while they process.

---

## Status Badges

Status badges appear on model cards and explorer/converter results throughout the interface:

| Badge             | Meaning                                           |
| ----------------- | ------------------------------------------------- |
| **Not Started**   | The operation has been configured but not yet run |
| **Finalizado**    | The operation completed successfully              |
| **Error**         | The operation failed — check parameters or data   |
| **Processing...** | The operation is currently running                |
| **Delivered**     | The result is available and displayed             |
