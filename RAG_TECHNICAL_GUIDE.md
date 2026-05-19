# DashAI: RAG Implementation Technical Guide

This document provides a detailed technical overview of the Retrieval-Augmented Generation (RAG) implementation in DashAI, covering both backend and frontend architectures, user flows, and the differences between the Simplified and Legacy views.

---

## 1. Backend Architecture

The RAG system is built upon the core generative framework of DashAI but extends it with document management and retrieval capabilities.

### 1.1 Data Models (SQLAlchemy)
Located in `DashAI/back/dependencies/database/models.py`, the key models are:
- **`Document`**: Stores metadata of uploaded files (name, path, hash, type).
- **`GenerativeSession`**: Stores the configuration of the RAG pipeline (chosen models and parameters).
- **`RAGPipeline`**: An extension that links a session with its specific RAG components.
- **`RAGChunk`**: Individual text segments extracted from documents.
- **`RAGChunkingModel` & `RAGDenseRetriever`**: Store parameters and types of the components used.

### 1.2 The RAG Pipeline (`RAGPipeline.py`)
This is the heart of the RAG logic. It orchestrates three main stages:
1.  **Ingestion/Chunking**: Uses a `BaseChunkingModel` to split documents into manageable pieces.
2.  **Retrieval**: Uses a `RetrieverModel` (e.g., TF-IDF, Vector Search) to find the most relevant chunks for a given query.
3.  **Generation**: Formats a prompt using a `Prompt` template and sends it to a `TextToTextGenerationTaskModel`.

### 1.3 Asynchronous Execution (`RAGJob.py`)
RAG operations are heavy and thus run as background jobs:
1.  User sends a message -> A `GenerativeProcess` is created.
2.  A `RAGJob` is enqueued in the `JobQueue`.
3.  The worker executes the job:
    - Instantiates the `RAGPipeline`.
    - Retrieves conversation history.
    - Runs `pipeline.generate(input_data)`.
    - Saves the output and reference metadata (source chunks) back to `ProcessData`.

---

## 2. Frontend Architecture

DashAI provides a single RAG interface: the **Simplified View** (`SimplifiedRAGPage`). This replaced the legacy `RAGHomePage` multi-step wizard (removed).

### 2.1 Simplified View (`SimplifiedRAGPage`)
**Goal:** Low-friction, guided setup for immediate use.
- **Route:** `/app/generative/rag`
- **Layout:** 3-panel (`LeftPanel` / `CenterPanel` / `RightPanel`)
- **Left Panel:** `SessionBar` (when no session) or `RAGDocumentsPanel` (when session selected)
- **Center Panel:** `SimplifiedSessionSetup` (creation) → `RAGSessionSummary` (overview) → `GenerativeChat` (active chat)
- **Right Panel:** `SimplifiedRAGInfoBar` (educational info during creation) or `RAGParamsPanel` (edit prompt + LLM when session selected)
- **Setup Flow:** Single-page with **Reactive Accordions** (Session Details, Documents, Chunking, Retriever, Prompt, Generator). Cancel/Save buttons are fixed at the bottom using a flex layout.
- **Navigation:** Selecting "RAG Task" from `/app/generative` navigates directly here. The "Simplified RAG Setup" task card was removed — only the standard "RAG Task" remains.

### 2.2 Dual Card System (Creation vs. Params Bar)

| Aspect | Creation (`PromptSection`/`GeneratorSection`) | Params Bar (`PromptParamsCard`/`GeneratorParamsCard`) |
|--------|----------------------------------------------|------------------------------------------------------|
| Description text | Always visible, no toggle | ℹ️ toggle to show/hide |
| Collapse | Handled by outer Accordion (no inner collapse) | Own `ExpandMoreIcon` toggle |
| Default state | Expanded (accordion) | Collapsed (selector visible) |
| Selector | Inside card body | Always visible even when collapsed |
| Shared core | `PromptBody` / `GeneratorBody` with `showDetails` prop | `PromptBody` / `GeneratorBody` with `showDetails` prop |

Both share `PromptBody` and `GeneratorBody` subcomponents. The `showDetails` prop controls whether template preview / context stats / advanced buttons are rendered.

### 2.3 Chunking Presets

Four presets with dynamic descriptions showing both character and approximate token counts:
- Small chunks (256 chars ≈ 64 tokens)
- Paragraph length (500 chars ≈ 125 tokens)  
- Page chunk (2000 chars ≈ 500 tokens)
- Large sections (4000 chars ≈ 1000 tokens)

Token estimation uses `Math.ceil(chars / 4)`. Descriptions are i18n-interpolated via `chunkSizeFormat` key. Toggle buttons use sentence case with `textTransform: "none"` to override MUI theme uppercase.

### 2.4 Document Preview

`DocumentPreviewModal` renders PDFs in an `<iframe>` and TXT files as `<pre>`. URLs are normalized via `utils/urlUtils.js` → `normalizeUrl()` which prepends `API_ORIGIN` (extracted from `REACT_APP_API_URL`) to relative paths. Backend `download_document` uses RFC 5987 `filename*=UTF-8''` encoding for Unicode filenames.

### 2.5 Sequential Session Naming

`SimplifiedSessionSetup` fetches sessions directly via `getSessions()` on mount (not relying on prop context chain). Uses `useState` + `useEffect` pattern instead of `useRef`-based tracking to avoid React 18 StrictMode double-fire bugs.

---

## 3. RAG Setup: Simplified vs. Standard Tasks

| Feature | Standard Gen Tasks | RAG Simplified |
| :--- | :--- | :--- |
| **Form Generation** | `ParameterForm` (Auto-generated from Schema) | Custom Reactive Accordions |
| **Logic Coupling** | Models are independent | Highly reactive (Cross-component validation) |
| **Data Source** | None (User input only) | Integrated `DocumentSelector` |
| **Right Panel** | Empty or Static Model Info | Educational info bar or Params editor |
| **User Onboarding** | Direct to Chat | Guided summary (`RAGSessionSummary`) |

### 3.1 Reactive Validation
`SimplifiedSessionSetup` calculates the remaining tokens for the LLM based on `chunk_size` × `top_k` + `prompt_token_count`. If the combined size exceeds the model's context window, it triggers a validation error *before* session creation.

### 3.2 Dynamic Naming
Session names are suggested sequentially (`RAG_Session_1`, `RAG_Session_2`, etc.) by querying existing RAG sessions from the backend at mount time and filtering by `task_name === "RAGTask"`.

---

## 4. Execution Flow (The Lifecycle of a Query)

1.  **Frontend (UI):** User types in `GenerativeChat`.
2.  **API call:** `POST /api/v1/generative_process/` sends the text and `session_id`.
3.  **Backend (API):** Creates the database records and enqueues the `RAGJob`.
4.  **Backend (Worker):**
    - `RAGPipeline` loads the selected `Retriever` (e.g., FAISS).
    - `Retriever` searches the `RAGChunk` table for matches.
    - `RAGTask` prepares the chat history.
    - The LLM generates the response using the context.
5.  **Database Storage:** The response is saved. Crucially, the **source chunks metadata** is stored as a second output item in `ProcessData`.
6.  **Frontend (UI):** `GenerativeChat` detects the source metadata and renders the "References" section using `DocumentReferencesModal`, allowing the user to see exactly where the information came from.

---

## 5. Summary of Interfaces

- **`DocumentSelector`**: Document picker used in creation form. Upload button positioned below the document table.
- **`DocumentsBar`**: Sidebar in the chat/summary view listing session documents.
- **`RAGDocumentsPanel`**: Left panel wrapper showing session documents.
- **`RAGBreadcrumbs`**: Navigation breadcrumbs for RAG sub-pages (`/app/generative/rag/*`).
- **`RAGSessionSummary`**: Session overview showing config details before entering chat.
- **`RAGParamsPanel`**: Right panel for editing prompt and LLM of an existing session.
- **`SimplifiedRAGInfoBar`**: Right panel with educational RAG content (shown during session creation).
- **`PromptBody` / `GeneratorBody`**: Shared core subcomponents with `showDetails` prop.
- **`PromptParamsCard` / `GeneratorParamsCard`**: Collapsible cards for the params bar (info toggle, selector always visible, collapsed by default).
- **`SectionCard`**: Consistent spacing wrapper used by Prompt and Generator creation sections.
- **`SimplifiedDocumentTable`**: MRT-based document table with checkbox selection and preview modal.

## 6. Component Visibility & Rendering Logic

### 6.1 Right Panel
- **`SimplifiedRAGInfoBar`**: Visible when no session is selected (creation phase). Provides educational guidance.
- **`RAGParamsPanel`**: Visible when a session is selected. Contains collapsible `PromptParamsCard` and `GeneratorParamsCard`.

### 6.2 Center Panel
- **`SimplifiedSessionSetup`**: Visible when no session is selected. All sections as reactive Accordions with sticky Cancel/Save buttons.
- **`RAGSessionSummary`**: Visible when a session is selected but chat is not active. Bridge between config and chat.
- **`GenerativeChat`**: Visible when user explicitly starts chat from summary.

### 6.3 Left Panel
- **`SessionBar`**: Visible when no session is selected. Lists all sessions.
- **`RAGDocumentsPanel`**: Visible when a session is selected. Shows session-specific documents.

### 6.4 Summary Table

| Component | Condition: No Session | Condition: Session Selected | Condition: Chat Active |
| :--- | :--- | :--- | :--- |
| **`DocumentsBar`** | Hidden | Visible (Session Docs) | Visible (Session Docs) |
| **`InfoBar`** | Visible | Hidden | Hidden |
| **`Setup`** | Visible | Hidden | Hidden |
| **`Summary`** | Hidden | Visible | Hidden |
| **`Chat`** | Hidden | Hidden | Visible |

---

## 7. Session Creation Lifecycle

### 7.1 Frontend: Initialization
The creation process begins in either `SimplifiedSessionSetup` or `NewSessionModal`.
1.  **Parameter Collection**: The UI gathers the selected documents (IDs), chunking strategy, retriever model, prompt ID, and LLM generator.
2.  **Pre-validation**:
    - **Simplified View**: Performs cross-component validation (e.g., checking if `chunk_size` * `top_k` fits in the LLM's context window).
    - **Legacy View**: Validates each step of the wizard independently.
3.  **API Call**: Triggers `POST /api/v1/generative_session/` with a JSON body containing `task_name="RAGTask"`, `model_name="RAGPipeline"`, and the `parameters` object.

### 7.2 Backend: Storage & Validation
The endpoint in `generative_session.py` handles the request:
1.  **Component Verification**: Checks if `RAGPipeline` and `RAGTask` are registered in the `ComponentRegistry`.
2.  **Document Validation**: For RAG specifically, it verifies that all provided document IDs exist in the database.
3.  **Schema Validation**: Runs `RAGPipeline.SCHEMA.model_validate(params)` to ensure all parameters (chunking, retriever, generator) are present and have valid types/values.
4.  **Persistence**:
    - Creates a `GenerativeSession` record.
    - Creates a `GenerativeSessionParameterHistory` entry to track the initial state.
    - Returns the session ID and metadata to the frontend.

---

## 8. Execution Workflow (Session Use)

### 8.1 Initiating a Query
1.  **Frontend**: The user sends a message through `GenerativeChat`.
2.  **Process Creation**: `POST /api/v1/generative_process/` is called.
    - Backend creates a `GenerativeProcess` with status `PENDING`.
    - Input text is stored in `ProcessData` linked to the process ID.

### 8.2 The Background Job (`RAGJob`)
The system enqueues a `RAGJob`. When a worker picks it up:
1.  **Pipeline Reconstruction**: The worker instantiates the `RAGPipeline` using the parameters stored in the `GenerativeSession`.
2.  **Retrieval Phase**: 
    - The query is sent to the `RetrieverModel`.
    - It searches the `RAGChunk` table (filtering by documents associated with the session).
    - Returns the Top-K most relevant chunks.
3.  **Generation Phase**:
    - Combines history + context chunks + user query into a single prompt string.
    - Calls the LLM's `generate()` method.
4.  **Persistence**:
    - Saves the response text to `ProcessData`.
    - Saves the **references** (metadata of chunks used) as a dictionary in `ProcessData` (type `Dict`).
    - Updates process status to `FINISHED`.

---

## 9. Prerequisites for Execution

For a RAG session to execute successfully, the following conditions must be met:

### 9.1 Technical Prerequisites
- **Component Registry**: The chosen chunking, retriever, and generation models must be correctly registered in DashAI's registry.
- **Database Consistency**:
    - The `Document` records must exist.
    - The physical files must exist in the path specified by `config["DOCUMENTS_PATH"]`.
    - If using a dense retriever, the embeddings must have been generated (handled during pipeline init).
- **Hardware Resources**:
    - Sufficient VRAM/RAM for the selected LLM.
    - Proper configuration of `llama-cpp` or `transformers` backends if using local models.

### 9.2 Functional Prerequisites (Validation)
- **Prompt Placeholders**: The selected prompt template **must** contain the placeholders `{chunks}` and `{input}`. Without these, the `RAGPipeline` cannot inject the retrieved context.
- **Context Window**: The sum of (tokens in history + tokens in prompt + tokens in retrieved chunks) must be less than the LLM's `max_context_length`.
- **Non-empty Documents**: The session must be associated with at least one document containing text.

---

## 10. Migration Summary (May 2026)

The legacy `RAGHomePage` and its multi-step wizard (`NewSessionModal`) have been removed. The simplified view is now the only RAG interface.

### 10.1 Files Deleted (19 total)

**Dead code (never imported):**
- `simplified-RAG/sections/index.js`, `simplified-RAG/advanced/index.js` — barrel files
- `components/generative/RAG/DocumentSelectionTable.jsx`, `SessionMetadata.jsx` — orphaned
- `pages/generative/RAG/AlgorithmConfigurationStep.jsx`, `ModelConfigurationStep.jsx`, `RetrieverConfigurationStep copy.jsx` — unused

**Legacy view:**
- `pages/generative/RAG/RAGHomePage.jsx`, `RAGSessionsPage.jsx`, `RAGSessionsTable.jsx`
- `pages/generative/RAG/NewSessionModal/` (6 files: NewSessionModal, 3 step components → relocated, ragFormDefaults → relocated)
- `components/generative/RAG/ComponentSelector.jsx`, `NewPromptModal.jsx` (consolidated into simplified version)

### 10.2 Files Relocated (4)

| Old path (`NewSessionModal/`) | New path (`simplified-RAG/`) |
|------|------|
| `ChunkingConfigurationStep.jsx` | `advanced/ChunkingConfigurationStep.jsx` |
| `RetrieverConfigurationStep.jsx` | `advanced/RetrieverConfigurationStep.jsx` |
| `GeneratorConfigurationStep.jsx` | `advanced/GeneratorConfigurationStep.jsx` |
| `ragFormDefaults.js` | `components/ragFormDefaults.js` |

### 10.3 Routes Updated

| Route | Before | After |
|-------|--------|-------|
| `/app/generative/rag` | `RAGHomePage` (legacy) | `SimplifiedRAGPage` |
| `/app/generative/rag/sessions` | `RAGSessionsPage` | Removed |
| `/app/generative/RAG` (uppercase) | `RAGHomePage` | Removed |
| `/app/generative/simplified-rag` | `SimplifiedRAGPage` | Removed (absorbed) |
| `/app/generative/rag/documents` | `RAGDocumentsPage` | Unchanged |
| `/app/generative/rag/prompts` | `RAGPromptsPage` | Unchanged |

### 10.4 Key Design Changes

- **SelectTaskMenu**: "Simplified RAG Setup" card removed. "RAG Task" navigates directly to `/app/generative/rag`.
- **SessionBar / RAGBreadcrumbs**: Fixed route from `/app/generative/RAG` to `/app/generative/rag`.
- **GenerativeContent**: No longer delegates to RAG — only handles non-RAG generative tasks.
- **Document preview**: `normalizeUrl()` with `API_ORIGIN` extraction fixes relative URL issue. Backend uses RFC 5987 encoding for Unicode filenames.
- **Sequential naming**: Direct `getSessions()` fetch on mount avoids React StrictMode ref-timing bug.
- **Sticky buttons**: Custom wrapper replaces `CenterBox` for RAG setup, with flex layout keeping Cancel/Save fixed at bottom.
- **DocumentSelector**: Upload button moved below table. `minHeight` removed for natural sizing.
- **SectionCard**: Replaced Card wrapper with plain Box to avoid nested padding issues.
- **Chunking presets**: Dynamic `[chars] caracteres ≈ [tokens] tokens` descriptions with i18n.

### 10.5 Files to Inspect (current state)

**Frontend:**
- `pages/generative/simplified-RAG/SimplifiedRAGPage.jsx` — entry point
- `pages/generative/simplified-RAG/SimplifiedSessionSetup.jsx` — creation form
- `pages/generative/simplified-RAG/components/PromptBody.jsx` — shared prompt core
- `pages/generative/simplified-RAG/components/GeneratorBody.jsx` — shared generator core
- `components/generative/RAG/PromptParamsCard.jsx` — params bar prompt card
- `components/generative/RAG/GeneratorParamsCard.jsx` — params bar generator card
- `components/generative/RAG/DocumentSelector.jsx` — document picker
- `components/generative/RAG/DocumentPreviewModal.jsx` — preview modal
- `utils/urlUtils.js` — URL normalization

**Backend:**
- `DashAI/back/api/api_v1/endpoints/documents.py` — file_url absolute URLs + RFC 5987 encoding

