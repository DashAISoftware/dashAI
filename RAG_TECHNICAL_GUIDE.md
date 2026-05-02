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

DashAI provides two distinct ways to interact with RAG, sharing the same underlying API but offering different user experiences.

### 2.1 Legacy View (`RAGHomePage`)
**Goal:** Full administrative control over the RAG ecosystem.
- **Components:** `RAGSessionsPage`, `RAGDocumentsPage`, `RAGPromptsPage`.
- **Setup Flow:** Uses `NewSessionModal`, a linear multi-step wizard (1. Documents -> 2. Chunking -> 3. Retriever -> 4. Prompt -> 5. Model).
- **Resource Management:** Documents and Prompts are managed in their own dedicated views before being selected in a session.

### 2.2 Simplified View (`SimplifiedRAGPage`)
**Goal:** Low-friction, guided setup for immediate use.
- **Component:** `SimplifiedSessionSetup.jsx`.
- **Setup Flow:** A single-page layout with **Reactive Accordions**. Instead of a wizard, it presents all sections (Chunking, Retriever, Prompt, Generator) in colapsable panels.
- **Contextual Info:** Uses the `RightPanel` to show a `SimplifiedRAGInfoBar` during setup, providing educational tooltips and status checks.

---

## 3. RAG Setup: Simplified vs. Legacy vs. Standard Tasks

| Feature | Standard Gen Tasks | RAG Legacy | RAG Simplified |
| :--- | :--- | :--- | :--- |
| **Form Generation** | `ParameterForm` (Auto-generated from Schema) | Custom multi-step wizard | Custom Reactive Accordions |
| **Logic Coupling** | Models are independent | Components are linked in a modal | Highly reactive (Cross-component validation) |
| **Data Source** | None (User input only) | Global document library | Integrated `DocumentSelector` |
| **Right Panel** | Empty or Static Model Info | Document management | Technical health monitor & Info bar |
| **User Onboarding** | Direct to Chat | Multi-step config | Guided summary (`RAGSessionSummary`) |

### 3.1 Reactive Validation in Simplified View
The `SimplifiedSessionSetup` implements logic that isn't present in standard tasks:
- **Token Window Calculation:** It calculates the remaining tokens for the LLM based on the `chunk_size` (from Chunking) and `top_k` (from Retriever). If the combined size exceeds the model's limit, it triggers a validation error *before* the session is created.
- **Dynamic Suggestions:** Suggests session names based on existing RAG sessions only.

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

- **`DocumentSelector`**: Shared component used to pick documents from the database.
- **`DocumentsBar`**: Persistent side-bar in the chat view that lists active files.
- **`RAGBreadcrumbs`**: Specialized navigation for the RAG module.
- **`RAGSessionSummary`**: An "entry hall" for a session showing its configuration health before starting the chat.

---

## 6. Component Visibility & Rendering Logic

The visibility of key RAG components depends on the current view (Simplified vs. Legacy) and the state of the session (Selected vs. Chat Active).

### 6.1 Right Panel Components
The right panel is dynamic and changes based on the user's context:

- **`DocumentsBar`**:
    - **In Legacy View**: Always visible. If no session is selected, it shows **all** database documents and allows uploads. If a session is selected, it filters to show only **session documents** and disables uploads.
    - **In Simplified View**: Visible **only when a session is selected**. It always shows the session-specific documents.
- **`SimplifiedRAGInfoBar`**:
    - **In Simplified View**: Visible **only during the configuration phase** (when no session is selected). It provides technical guidance for the accordions.
    - **In Legacy View**: Never visible.

### 6.2 Center Panel States
The center panel manages the primary interaction flow:

- **`SimplifiedSessionSetup`**: Visible only in Simplified View when `selectedSessionId` is null.
- **`RAGHomePage` (Option Menu)**: Visible only in Legacy View when `selectedSessionId` is null.
- **`RAGSessionSummary`**: Visible in **both views** when a session is selected but the chat is not yet active (`!isRagChatActive`). It acts as a bridge between configuration and conversation.
- **`GenerativeChat`**: Visible in **both views** only when the user explicitly starts the interaction from the summary screen.

### 6.3 Summary Table of States

| Component | View | Condition: No Session | Condition: Session Selected | Condition: Chat Active |
| :--- | :--- | :--- | :--- | :--- |
| **`DocumentsBar`** | Legacy | Visible (All Docs) | Visible (Session Docs) | Visible (Session Docs) |
| **`DocumentsBar`** | Simplified | Hidden | Visible (Session Docs) | Visible (Session Docs) |
| **`InfoBar`** | Simplified | Visible | Hidden | Hidden |
| **`Setup/Menu`** | Both | Visible | Hidden | Hidden |
| **`Summary`** | Both | Hidden | Visible | Hidden |
- **`Chat`**: Both | Hidden | Hidden | Visible |

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

