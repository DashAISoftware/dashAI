import api from "./api";
import { ISession } from "../types/session";
import { IGenerativeTask } from "../types/generativeTask";





// Dummy data
// use the days of june 2025 for first, second, ... sessions
let sessions: ISession[] = [
  {
    id: "1",
    name: "Session I",
    task_name: "RAGTask",
    description: "First dummy session",
    created: new Date("2025-06-01"),
    last_modified: new Date("2025-06-01"),
    display_name: "RAG Session I",
    model_name: "RAGModel",
    parameters: { paramA: 1 },
  },
  {
    id: "2",
    name: "Session II",
    task_name: "RAGTask",
    description: "Second dummy session",
    created: new Date("2025-06-02"),
    last_modified: new Date("2025-06-02"),
    display_name: "RAG Session II",
    model_name: "RAGModel",
    parameters: { paramA: 2 },
  },
  {
    id: "3",
    name: "Session III",
    task_name: "RAGTask",
    description: "Third dummy session",
    created: new Date("2025-06-03"),
    last_modified: new Date("2025-06-03"),
    display_name: "RAG Session III",
    model_name: "RAGModel",
    parameters: { paramA: 3 },
  },
  {
    id: "4",
    name: "Session IV",
    task_name: "RAGTask",
    description: "Fourth dummy session",
    created: new Date("2025-06-04"),
    last_modified: new Date("2025-06-04"),
    display_name: "RAG Session IV",
    model_name: "RAGModel",
    parameters: { paramA: 4 },
  }
];

let components: IGenerativeTask[] = [
  {
    name: "Dense Passage Retrieval",
    type: "retriever",
    configurable_object: true,
    schema: {
      description: "Schema for dense passage retrieval",
      properties: {
        paramA: {
          description: "Transformer",
          enum: [
            "BERT",
            "RoBERTa",
            "DistilBERT",
            "ALBERT",
          ],
          placeholder: "BERT",
          title: "Parameter A",
          type: "string",
        },
        DistanceMetric: {
          description: "Distance metric to use for retrieval",
          enum: [
            "cosine",
            "dot_product",
            "euclidean",
          ],
          placeholder: "cosine",
          title: "Distance Metric",
          type: "string",
        },
      },
      required: ["paramA", "DistanceMetric"],
      type: "object",
    },
    metadata: {
      inputs_cardinality: 1,
      outputs_cardinality: 1,
      inputs_types: ["text"],
      outputs_types: ["text"],
    },
    description: "A component for dense passage retrieval",
    display_name: "Dense Passage Retrieval",
  },
  {
    name: "TFIDFRetriever",
    type: "retriever",
    configurable_object: true,
    schema: {
      description: "Schema for TF-IDF retriever",
      properties: {
        paramA: {
          description: "Remove stop words",
          placeholder: "true",
          title: "Remove Stop Words",
          type: "boolean"
        },
        TokenScoreCombination: {
          description: "Token score combination method",
          enum: [
            "sum",
            "max",
            "min",
          ],
          placeholder: "sum",
          title: "Token Score Combination",
          type: "string"
        },
      },
      required: ["paramA", "TokenScoreCombination"],
      type: "object",
    },
    metadata: {
      inputs_cardinality: 1,
      outputs_cardinality: 1,
      inputs_types: ["text"],
      outputs_types: ["text"],
    },
    description: "A component for TF-IDF retrieval",
    display_name: "TF-IDF Retriever",
  },

  {
      name: "DeepSeekModel",
      type: "GenerativeModel",
      configurable_object: true,
      schema: {
          description: "Schema for DeepSeek model.",
          properties: {
              max_tokens: {
                  description: "Maximum number of tokens to generate.",
                  minimum: 1,
                  placeholder: 100,
                  title: "Max Tokens",
                  type: "integer"
              },
              temperature: {
                  description: "Sampling temperature. Higher values make the output more random, while lower values make it more focused and deterministic.",
                  maximum: 1,
                  minimum: 0,
                  placeholder: 0.7,
                  title: "temperature",
                  type: "number"
              },
              frequency_penalty: {
                  description: "Penalty for repeated tokens in the output. Higher values reduce the likelihood of repetition, encouraging more diverse text generation.",
                  maximum: 2,
                  minimum: 0,
                  placeholder: 0.1,
                  title: "Frequency Penalty",
                  type: "number"
              },
              n_ctx: {
                  description: "Maximum number of tokens the model can process in a single forward pass (context window size).",
                  minimum: 1,
                  placeholder: 4096,
                  title: "N Ctx",
                  type: "integer"
              }
          },
          required: [
              "max_tokens",
              "temperature",
              "frequency_penalty",
              "n_ctx"
          ],
          title: "DeepSeekSchema",
          type: "object"
      },
      metadata: {
          inputs_cardinality: 1,
          outputs_cardinality: 1,
          inputs_types: ["text"],
          outputs_types: ["text"]
      },
      description: "null,",
      display_name: "null"
  },
  {
      name: "GemmaModel",
      type: "GenerativeModel",
      configurable_object: true,
      schema: {
          description: "Schema for Gemma model.",
          properties: {
              max_tokens: {
                  description: "Maximum number of tokens to generate.",
                  minimum: 1,
                  placeholder: 100,
                  title: "Max Tokens",
                  type: "integer"
              },
              temperature: {
                  description: "Sampling temperature. Higher values make the output more random, while lower values make it more focused and deterministic.",
                  maximum: 1,
                  minimum: 0,
                  placeholder: 0.7,
                  title: "temperature",
                  type: "number"
              },
              frequency_penalty: {
                  description: "Penalty for repeated tokens in the output. Higher values reduce the likelihood of repetition, encouraging more diverse text generation.",
                  maximum: 2,
                  minimum: 0,
                  placeholder: 0.1,
                  title: "Frequency Penalty",
                  type: "number"
              },
              n_ctx: {
                  description: "Maximum number of tokens the model can process in a single forward pass (context window size).",
                  minimum: 1,
                  placeholder: 512,
                  title: "N Ctx",
                  type: "integer"
              }
          },
          required: [
              "max_tokens",
              "temperature",
              "frequency_penalty",
              "n_ctx"
          ],
          title: "GemmaSchema",
          type: "object"
      },
      metadata: {
          inputs_cardinality: 1,
          outputs_cardinality: 1,
          inputs_types: ["text"],
          outputs_types: ["text"]
      },
      description: "null,",
      display_name: "null"
  },
  {
      name: "QwenModel",
      type: "GenerativeModel",
      configurable_object: true,
      schema: {
          description: "Schema for Qwen model.",
          properties: {
              "model_name": {
                  description: "The specific Qwen model version to use.",
                  "enum": [
                      "Qwen/Qwen2.5-0.5B-Instruct-GGUF",
                      "Qwen/Qwen2.5-1.5B-Instruct-GGUF"
                  ],
                  placeholder: "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
                  title: "Model Name",
                  type: "string"
              },
              max_tokens: {
                  description: "Maximum number of tokens to generate.",
                  minimum: 1,
                  placeholder: 100,
                  title: "Max Tokens",
                  type: "integer"
              },
              temperature: {
                  description: "Sampling temperature. Higher values make the output more random, while lower values make it more focused and deterministic.",
                  maximum: 1,
                  minimum: 0,
                  placeholder: 0.7,
                  title: "temperature",
                  type: "number"
              },
              frequency_penalty: {
                  description: "Penalty for repeated tokens in the output. Higher values reduce the likelihood of repetition, encouraging more diverse text generation.",
                  maximum: 2,
                  minimum: 0,
                  placeholder: 0.1,
                  title: "Frequency Penalty",
                  type: "number"
              },
              n_ctx: {
                  description: "Maximum number of tokens the model can process in a single forward pass (context window size).",
                  minimum: 1,
                  placeholder: 512,
                  title: "N Ctx",
                  type: "integer"
              }
          },
          required: [
              "model_name",
              "max_tokens",
              "temperature",
              "frequency_penalty",
              "n_ctx"
          ],
          title: "QwenSchema",
          type: "object"
      },
      metadata: {
          inputs_cardinality: 1,
          outputs_cardinality: 1,
          inputs_types: ["text"],
          outputs_types: ["text"]
      },
      description: "null,",
      display_name: "null"
  }
]

// Fetch all RAG sessions
export const getRAGSessions = async (): Promise<ISession[]> => {
  console.log("Fetching all RAG sessions");

  // Simulate an API call
  /*
  const response = await api.get<ISession[]>(
    "/v1/generative-session
  */
  return [...sessions];
}

// Create a new RAG session
export const createRAGSession = async (
  sessionData: Omit<ISession, "id" | "created_at">
): Promise<ISession> => {
  const newSession: ISession = {
    ...sessionData,
    id: (Math.random() * 100000).toFixed(0),
  };
  // Simulate an API call
  /*
  const response = await api.post<RAGSession>("/v1/rag-session/", newSession);
  */
  sessions.push(newSession);
  return newSession;
}

// Update an existing RAG session
export const updateRAGSession = async (
  sessionData: ISession
): Promise<ISession> => {
  
  // Mockup data
  const index = sessions.findIndex((s) => s.id === sessionData.id);
  if (index === -1) throw new Error("Session not found");
  sessions[index] = sessionData;

  // Simulate an API call
  /*
  const response = await api.put<RAGSession>(
    `/v1/rag-session/${sessionData.id}`,
    sessionData
  );
  */

  return sessionData;
}

// Delete a RAG session by ID
export const deleteRAGSession = async (sessionId: string): Promise<void> => {
  
  // mockup data
  sessions = sessions.filter((s) => s.id !== sessionId);

  // Simulate an API call
  /*
  removeSession(sessionId);
  */

  console.log(`Deleted session with ID: ${sessionId}`);
  return;
}

// Fetch a single RAG session by ID
export const getRAGSession = async (sessionId: string): Promise<ISession[]> => {
  console.log(`Fetching session with ID: ${sessionId}`);

  // Simulate an API call
  /*
  const response = await api.get<ISession>(
    `/v1/generative-session/${sessionId}`

  return response.data;
  */
  
  const session = sessions.find((s) => s.id === sessionId);
  if (!session) throw new Error("Session not found");

  return [session];
}

export const getRAGComponents = async (componentType: string): Promise<IGenerativeTask[]> => {
  // Simulate fetching RAG components based on type
  /* 
  const response = await api.get(
    `/v1/component/?related_component=RAGTask&component_type=${componentType}`
  );
  return response.data; 
  */
 
 let filteredComponents = components.filter((c) => c.type === componentType);
 console.log(`Fetching RAG ${filteredComponents.length} components of type ${componentType}`);
 return filteredComponents;
};

export const getRetrieverComponents = async (): Promise<IGenerativeTask[]> => {
  return getRAGComponents("retriever");
}

export const getGeneratorComponents = async (): Promise<IGenerativeTask[]> => {
  return getRAGComponents("GenerativeModel");
}