import React from "react";
import { screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../../test-utils/renderWithProviders";
import TraceChunksPanel from "./TraceChunksPanel";
import { TRACE_VIEW_PIPELINE } from "../../../constants/rag";
import { getRetrievalParadigm } from "../../../api/rag";

jest.mock("../../../api/rag", () => ({
  getRetrievalParadigm: jest.fn(),
  getSessionConfiguration: jest.fn(),
}));
jest.mock("notistack", () => ({
  useSnackbar: () => ({ enqueueSnackbar: jest.fn() }),
}));

const REFERENCES = {
  "1_0": {
    document_id: 1,
    document_name: "Alpha.pdf",
    document_position: 0,
    text: "alpha",
  },
  "1_1": {
    document_id: 1,
    document_name: "Alpha.pdf",
    document_position: 1,
    text: "beta",
  },
};

const QUERY_ENTRIES = [
  { query: "first", retriever: { name: "BM25Retriever", chunks: ["1_0"] } },
  {
    query: "second",
    retriever: { name: "BM25Retriever", chunks: ["1_0", "1_1"] },
  },
];

const RERANK_ENTRY = {
  stage: "rerank",
  reranker: {
    name: "DenseEmbeddingRetriever",
    chunks: ["1_0"],
    pool: ["1_0", "1_1", "1_2"],
  },
};

const renderPanel = (trace) =>
  renderWithProviders(
    <TraceChunksPanel
      activeView={TRACE_VIEW_PIPELINE}
      onClose={jest.fn()}
      userMessage="original question"
      trace={trace}
      references={REFERENCES}
    />,
  );

beforeEach(() => {
  getRetrievalParadigm.mockResolvedValue([]);
});

describe("TraceChunksPanel pool reranking", () => {
  it("draws the rerank tree under the query trees in the All view", async () => {
    renderPanel([...QUERY_ENTRIES, RERANK_ENTRY]);

    const rerankTree = await screen.findByTestId("rerank-tree");
    expect(rerankTree).toHaveTextContent(/3\D+1/);
    expect(
      within(rerankTree).getByText("DenseEmbeddingRetriever"),
    ).toBeInTheDocument();
    await waitFor(() => expect(getRetrievalParadigm).toHaveBeenCalled());
  });

  it("leaves the query entries and the query selector unchanged", async () => {
    renderPanel([...QUERY_ENTRIES, RERANK_ENTRY]);

    await screen.findByTestId("rerank-tree");
    expect(screen.getAllByTestId("query-chip")).toHaveLength(3);
  });

  it("hides the rerank tree once a single query is selected", async () => {
    renderPanel([...QUERY_ENTRIES, RERANK_ENTRY]);
    await screen.findByTestId("rerank-tree");

    await userEvent.click(screen.getAllByTestId("query-chip")[1]);

    expect(screen.queryByTestId("rerank-tree")).not.toBeInTheDocument();
  });

  it("renders no rerank tree when the trace has no rerank entry", async () => {
    renderPanel(QUERY_ENTRIES);

    await screen.findByTestId("trace-tree");
    expect(screen.queryByTestId("rerank-tree")).not.toBeInTheDocument();
  });
});
