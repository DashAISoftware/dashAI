# End-to-End Execution Flow

## Step-by-Step

### 1. Form Submission
User fills the `RAGSessionSetup` form (documents, chunking, retriever, prompt, generator) and clicks Save.

### 2. Session Creation
Frontend calls `POST /api/v1/generative-session/`. The endpoint validates parameters against `RAGPipeline.SCHEMA` and persists the session record.

### 3. Process Creation
Frontend calls `POST /api/v1/generative-process/` with the user's input question. This creates a `GenerativeProcess` record linked to the session.

### 4. Job Dispatch
Frontend calls `POST /api/v1/job/` with `job_type="GenerativeJob"`. The job is enqueued in Huey (the async task queue).

### 5. Job Execution
`GenerativeJob.run()` detects the session uses `RAGTask` and delegates to `RAGJob.run()`.

### 6. Pipeline Construction
`RAGJob.run()`:
1. Constructs `RAGPipelineConfig` from the session parameters.
2. Instantiates `RAGModelsFactory` to resolve/create model records (chunking, retriever, prompt, LLM).
3. Creates `PipelineRepository` for persistence.
4. Creates `DocumentLoader` for document access.
5. Assembles `RAGPipeline` with all dependencies.

### 7. Generation
`RAGPipeline.generate()`:
1. **Load documents** — `DocumentLoader.load()` fetches document texts from the repository.
2. **Get or create chunk set** — `get_or_create_chunk_set()` computes a SHA-256 hash of the document IDs + chunking params. If a chunk set with that hash exists, reuse it; otherwise chunk and persist.
3. **Chunk** — The chunking model splits documents into chunks.
4. **Retrieve** — The retriever scores chunks against the query and returns the top-k.
5. **Build prompt** — The prompt template is rendered with retrieved chunks and the user query.
6. **Generate** — The LLM generates a response from the prompt.

### 8. Output Serialization
`RAGTask.process_output()` serializes retrieved chunks as JSON and saves the generation result to the database via the process record.

### 9. Frontend Polling
The frontend polls `GET /api/v1/jobs/{job_id}` for job status. When the job completes, it reads the process output and renders the chat response.
