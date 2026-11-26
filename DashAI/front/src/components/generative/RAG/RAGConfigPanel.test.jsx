import React from "react";
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../../test-utils/renderWithProviders";
import RAGConfigPanel from "./RAGConfigPanel";

jest.mock("react-markdown", () => ({
  __esModule: true,
  default: ({ children }) => <span>{children}</span>,
}));

jest.mock("notistack", () => {
  const snackbar = { enqueueSnackbar: jest.fn() };
  return { useSnackbar: () => snackbar };
});

jest.mock("../../../api/rag", () => ({
  getChunkingPresets: jest.fn(),
  getRAGSession: jest.fn(),
  getRetrieverComponents: jest.fn(),
  getRetrieverPresets: jest.fn(),
  getSessionConfiguration: jest.fn(),
  updateGenerativeSessionParams: jest.fn(),
  getDefaultPrompts: jest.fn(),
  getLibraryPrompts: jest.fn(),
  getQueryTransformationComponents: jest.fn(),
  getQueryTransformationPrompts: jest.fn(),
  getGeneratorComponents: jest.fn(),
}));
// The picker loads its options through this hook, which updates state after
// the test body has finished; the panel only needs a settled, empty answer.
jest.mock("../../../hooks/useQueryTransformationOptions", () => {
  const options = {
    transformers: [],
    prompts: [],
    generators: [],
    loading: false,
    loadError: null,
  };
  return { __esModule: true, default: () => options };
});
jest.mock("../../../api/session", () => ({
  updateGenerativeSession: jest.fn(),
}));
// The generator picker fetches components and download state of its own; the
// panel only cares about the availability it reports back.
jest.mock("./GeneratorPicker", () => {
  const MockGeneratorPicker = () => <div data-testid="generator-picker" />;
  return MockGeneratorPicker;
});
jest.mock(
  "../../../pages/generative/RAGSession/advanced/ChunkingAdvancedModal",
  () => {
    const MockChunkingAdvancedModal = () => null;
    return MockChunkingAdvancedModal;
  },
);
jest.mock(
  "../../../pages/generative/RAGSession/advanced/RetrieverAdvancedModal",
  () => {
    const MockRetrieverAdvancedModal = ({
      open,
      retrieverModel,
      setRetrieverModel,
    }) => {
      if (!open) return null;
      const setParams = (changes) =>
        setRetrieverModel({
          ...retrieverModel,
          params: { ...retrieverModel.params, ...changes },
        });
      const setChildrenTopK = (topK) =>
        setRetrieverModel({
          ...retrieverModel,
          params: {
            ...retrieverModel.params,
            children: retrieverModel.params.children.map((child) => ({
              ...child,
              params: { ...child.params, top_k: topK },
            })),
          },
        });
      return (
        <div>
          <button onClick={() => setParams({ top_k: 9 })}>
            Set chunk count to 9
          </button>
          <button
            onClick={() => setParams({ enable_retrieve_then_expand: true })}
          >
            Enable expansion
          </button>
          <button onClick={() => setChildrenTopK(2)}>
            Set child chunk counts to 2
          </button>
          <button
            onClick={() => setRetrieverModel({ component: "", params: {} })}
          >
            Clear retriever selection
          </button>
          <button
            onClick={() => setRetrieverModel({ component: "BM25Retriever" })}
          >
            Drop retriever params
          </button>
        </div>
      );
    };
    return MockRetrieverAdvancedModal;
  },
);

const api = require("../../../api/rag");

const CHUNKING_PRESETS = [
  {
    key: "balanced",
    display_name: "Balanced",
    description: "A middling chunk size",
    component: "CharacterChunkModel",
    params: { chunk_size: 400, chunk_overlap: 40 },
  },
  {
    key: "fine",
    display_name: "Fine",
    description: "Smaller chunks",
    component: "CharacterChunkModel",
    params: { chunk_size: 200, chunk_overlap: 20 },
  },
];

const RETRIEVER_PRESETS = [
  {
    key: "keyword",
    display_name: "Keyword",
    description: "BM25",
    component: "BM25Retriever",
    params: { top_k: 5 },
  },
];

const SESSION = {
  id: 1,
  name: "A session",
  description: "",
  parameters: {
    documents: [],
    chunking_model: CHUNKING_PRESETS[0],
    retriever_model: RETRIEVER_PRESETS[0],
    prompt: {
      component: "CustomRAGGenerationPrompt",
      params: { template: "Use {chunks} for {input}", language: "en" },
    },
    generation_model: { component: "StubLLM", params: {} },
  },
};

/** The shape `getSessionConfiguration` returns, with backend-localized names. */
const CONFIGURATION = {
  chunking_model: {
    section_name: "Chunking",
    component: "CharacterChunkModel",
    display_name: "Character",
    description: "How documents are split",
    registered: true,
    params: [],
    preset_key: "balanced",
    preset_display_name: "Balanced",
    summary: "400 characters",
  },
  query_transformation: {
    section_name: "Query Transformation",
    component: null,
    display_name: null,
    description: null,
    registered: false,
    params: [],
    enabled: false,
  },
  retriever_model: {
    section_name: "Retrieval",
    component: "BM25Retriever",
    display_name: "BM25",
    description: "How passages are found",
    registered: true,
    params: [],
    preset_key: "keyword",
    preset_display_name: "Keyword",
    top_k: 5,
  },
  generation_model: {
    section_name: "Model",
    component: "StubLLM",
    display_name: "Stub",
    description: "Which model answers",
    registered: true,
    params: [],
  },
  prompt: {
    section_name: "Prompt",
    component: "CustomRAGGenerationPrompt",
    display_name: "Custom",
    description: "How the question is phrased",
    registered: true,
    params: [],
  },
  context_budget: {
    context_window: 4096,
    available: 3000,
    is_valid: true,
  },
};

beforeEach(() => {
  jest.clearAllMocks();
  api.getRAGSession.mockResolvedValue(SESSION);
  api.getSessionConfiguration.mockResolvedValue(CONFIGURATION);
  api.getChunkingPresets.mockResolvedValue(CHUNKING_PRESETS);
  api.getRetrieverPresets.mockResolvedValue(RETRIEVER_PRESETS);
  api.getRetrieverComponents.mockResolvedValue([]);
  api.updateGenerativeSessionParams.mockResolvedValue({});
  api.getDefaultPrompts.mockResolvedValue([]);
  api.getLibraryPrompts.mockResolvedValue([]);
  api.getQueryTransformationComponents.mockResolvedValue([]);
  api.getQueryTransformationPrompts.mockResolvedValue([]);
  api.getGeneratorComponents.mockResolvedValue([]);
});

/** Renders the panel and waits for its initial load. */
async function renderPanel(props = {}) {
  const onSaved = jest.fn();
  const onRetryIndexing = jest.fn();
  renderWithProviders(
    <RAGConfigPanel
      sessionId={1}
      onSaved={onSaved}
      onRetryIndexing={onRetryIndexing}
      {...props}
    />,
  );
  await screen.findByRole("button", { name: /Chunking/ });
  return { onSaved, onRetryIndexing };
}

test("renders one section per part, labelled by the backend", async () => {
  await renderPanel();
  for (const label of ["Chunking", "Retrieval", "Model", "Prompt"]) {
    expect(
      screen.getByRole("button", { name: new RegExp(label) }),
    ).toBeInTheDocument();
  }
});

test("saving is offered only once something changed", async () => {
  await renderPanel();
  const save = screen.getByRole("button", { name: /Save/i });
  expect(save).toBeDisabled();

  await userEvent.click(screen.getByText("Fine"));
  await waitFor(() => expect(save).toBeEnabled());
});

test("an edit in a collapsed section is still reported and still saved", async () => {
  await renderPanel();

  await userEvent.click(screen.getByText("Fine"));
  await userEvent.click(screen.getByRole("button", { name: /Model/ }));

  const chunkingHeader = screen.getByRole("button", { name: /Chunking/ });
  expect(
    within(chunkingHeader).getByTestId("FiberManualRecordIcon"),
  ).toBeInTheDocument();

  const save = screen.getByRole("button", { name: /Save/i });
  await waitFor(() => expect(save).toBeEnabled());
  await userEvent.click(save);

  await waitFor(() =>
    expect(api.updateGenerativeSessionParams).toHaveBeenCalledTimes(1),
  );
  const [, sent] = api.updateGenerativeSessionParams.mock.calls[0];
  expect(sent.chunking_model.params.chunk_size).toBe(200);
  expect(sent.retriever_model).toEqual(RETRIEVER_PRESETS[0]);
  expect(sent.prompt.params.template).toBe("Use {chunks} for {input}");
});

test("discarding puts every tab back to the saved configuration", async () => {
  await renderPanel();

  await userEvent.click(screen.getByText("Fine"));
  const discard = screen.getByRole("button", { name: /Discard/i });
  await waitFor(() => expect(discard).toBeEnabled());

  await userEvent.click(discard);

  await waitFor(() =>
    expect(screen.getByRole("button", { name: /Save/i })).toBeDisabled(),
  );
  expect(api.updateGenerativeSessionParams).not.toHaveBeenCalled();
});

test("every section is mounted, so one never opened still validates", async () => {
  await renderPanel();
  expect(screen.getByTestId("generator-picker")).toBeInTheDocument();
});

test("an unsaved Top K change keeps the retriever preset, another option does not", async () => {
  const keywordRef = {
    component: "BM25Retriever",
    params: {
      top_k: 5,
      vectorizer: "bag_of_words",
      enable_retrieve_then_expand: false,
      expand_window: 1,
    },
  };
  api.getRetrieverPresets.mockResolvedValue([
    {
      key: "keyword",
      display_name: "Keyword",
      description: "BM25",
      ...keywordRef,
    },
  ]);
  api.getRAGSession.mockResolvedValue({
    ...SESSION,
    parameters: { ...SESSION.parameters, retriever_model: keywordRef },
  });
  await renderPanel();
  const keywordChip = () => screen.getByRole("button", { name: /^Keyword/ });

  await userEvent.click(screen.getByRole("button", { name: /Retrieval/ }));
  const retrieval = within(
    screen.getByRole("heading", { name: /Retrieval/, level: 3 }).parentElement,
  );
  await userEvent.click(
    retrieval.getByRole("button", { name: /Advanced configuration/ }),
  );

  await userEvent.click(
    screen.getByRole("button", { name: "Set chunk count to 9" }),
  );
  await waitFor(() =>
    expect(screen.getByRole("button", { name: /Save/i })).toBeEnabled(),
  );
  expect(keywordChip()).toHaveAttribute("aria-pressed", "true");

  await userEvent.click(
    screen.getByRole("button", { name: "Enable expansion" }),
  );
  await waitFor(() =>
    expect(keywordChip()).toHaveAttribute("aria-pressed", "false"),
  );
});

test("an unsaved child Top K change keeps the hybrid preset selected", async () => {
  const hybridParams = {
    top_k: 10,
    children: [
      {
        component: "BM25Retriever",
        params: { top_k: 5, vectorizer: "bag_of_words" },
      },
      {
        component: "SemanticRetriever",
        params: { top_k: 5, similarity_metric: "cosine" },
      },
    ],
  };
  api.getRetrieverPresets.mockResolvedValue([
    {
      key: "hybrid",
      display_name: "Hybrid",
      description: "Keyword and semantic",
      component: "HybridRetriever",
      params: hybridParams,
    },
  ]);
  api.getRAGSession.mockResolvedValue({
    ...SESSION,
    parameters: {
      ...SESSION.parameters,
      retriever_model: {
        component: "HybridRetriever",
        params: JSON.parse(JSON.stringify(hybridParams)),
      },
    },
  });
  api.getSessionConfiguration.mockResolvedValue({
    ...CONFIGURATION,
    retriever_model: {
      ...CONFIGURATION.retriever_model,
      component: "HybridRetriever",
      display_name: "Hybrid",
      preset_key: "hybrid",
      preset_display_name: "Hybrid",
      top_k: 10,
    },
  });
  await renderPanel();
  const hybridChip = () => screen.getByRole("button", { name: /^Hybrid/ });

  await userEvent.click(screen.getByRole("button", { name: /Retrieval/ }));
  expect(hybridChip()).toHaveAttribute("aria-pressed", "true");
  const retrieval = within(
    screen.getByRole("heading", { name: /Retrieval/, level: 3 }).parentElement,
  );
  await userEvent.click(
    retrieval.getByRole("button", { name: /Advanced configuration/ }),
  );

  await userEvent.click(
    screen.getByRole("button", { name: "Set child chunk counts to 2" }),
  );
  await waitFor(() =>
    expect(screen.getByRole("button", { name: /Save/i })).toBeEnabled(),
  );
  expect(hybridChip()).toHaveAttribute("aria-pressed", "true");
});

test("a running index shows its progress, using the backend's wording", async () => {
  await renderPanel({
    indexStatus: {
      status: "indexing",
      message: "Indexing the documents…",
      job: { status: "started", progress: 40 },
    },
  });

  const notice = screen.getByRole("alert");
  expect(
    within(notice).getByText("Indexing the documents…"),
  ).toBeInTheDocument();
  expect(within(notice).getByRole("progressbar")).toHaveAttribute(
    "aria-valuenow",
    "40",
  );
});

test("an index with no progress yet shows an indeterminate bar", async () => {
  await renderPanel({
    indexStatus: {
      status: "indexing",
      message: "Indexing the documents…",
      job: { status: "not_started", progress: null },
    },
  });

  const notice = screen.getByRole("alert");
  expect(within(notice).getByRole("progressbar")).not.toHaveAttribute(
    "aria-valuenow",
  );
});

test("a stale index warns without claiming to be working", async () => {
  await renderPanel({
    indexStatus: {
      status: "stale",
      message: "The configuration changed.",
      job: null,
    },
  });

  const notice = screen.getByRole("alert");
  expect(
    within(notice).getByText("The configuration changed."),
  ).toBeInTheDocument();
  expect(within(notice).queryByRole("progressbar")).not.toBeInTheDocument();
});

test("a failed index stays visible and offers a retry", async () => {
  const { onRetryIndexing } = await renderPanel({
    indexStatus: {
      status: "not_indexed",
      message: "These documents are not indexed yet.",
      job: { status: "error", error: "Out of memory" },
    },
  });

  const notice = screen.getByRole("alert");
  expect(within(notice).getByText("Out of memory")).toBeInTheDocument();
  await userEvent.click(within(notice).getByRole("button", { name: /Retry/i }));
  expect(onRetryIndexing).toHaveBeenCalledTimes(1);
});

test("a job that finished cleanly raises no alarm", async () => {
  await renderPanel({
    indexStatus: {
      status: "indexed",
      message: "The documents are indexed.",
      job: { status: "finished", progress: 100, error: null },
    },
  });

  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

test.each([
  ["has no retriever_model", { retriever_model: undefined }, "retriever_model"],
  [
    "has a retriever_model with no component",
    { retriever_model: { component: "", params: {} } },
    "retriever_model",
  ],
  [
    "has a chunking_model with no params",
    { chunking_model: { component: "CharacterChunkModel" } },
    "chunking_model",
  ],
])(
  "a session that %s shows the load-failed alert instead of the panel",
  async (_label, overrides, invalidSection) => {
    const consoleError = jest
      .spyOn(console, "error")
      .mockImplementation(() => {});
    try {
      api.getRAGSession.mockResolvedValue({
        ...SESSION,
        parameters: { ...SESSION.parameters, ...overrides },
      });
      renderWithProviders(<RAGConfigPanel sessionId={1} />);

      const alert = await screen.findByRole("alert");
      expect(
        within(alert).getByText("Failed to load RAG session"),
      ).toBeInTheDocument();
      expect(
        within(alert).getByRole("button", { name: /Retry/i }),
      ).toBeVisible();
      expect(
        screen.queryByRole("button", { name: /Retrieval/ }),
      ).not.toBeInTheDocument();
      expect(consoleError).toHaveBeenCalledWith(
        "Failed to load RAG configuration:",
        expect.objectContaining({
          message: expect.stringContaining(invalidSection),
        }),
      );
    } finally {
      consoleError.mockRestore();
    }
  },
);

/** Opens the retrieval section's advanced dialog, which the mock renders. */
async function openRetrievalAdvanced() {
  await userEvent.click(screen.getByRole("button", { name: /Retrieval/ }));
  const retrieval = within(
    screen.getByRole("heading", { name: /Retrieval/, level: 3 }).parentElement,
  );
  await userEvent.click(
    retrieval.getByRole("button", { name: /Advanced configuration/ }),
  );
}

test("a cleared retriever selection is a custom config, not an error", async () => {
  await renderPanel();
  await openRetrievalAdvanced();

  await userEvent.click(
    screen.getByRole("button", { name: "Clear retriever selection" }),
  );

  await waitFor(() =>
    expect(screen.getByRole("button", { name: /Save/i })).toBeEnabled(),
  );
  expect(screen.getByRole("button", { name: /^Keyword/ })).toHaveAttribute(
    "aria-pressed",
    "false",
  );
});

test("a retriever reference with no params is malformed, not a cleared selection", async () => {
  const consoleError = jest
    .spyOn(console, "error")
    .mockImplementation(() => {});
  try {
    await renderPanel();
    await openRetrievalAdvanced();

    const dropParams = screen.getByRole("button", {
      name: "Drop retriever params",
    });
    expect(() => fireEvent.click(dropParams)).toThrow(
      "ref must be a {component, params} object",
    );
  } finally {
    consoleError.mockRestore();
  }
});
