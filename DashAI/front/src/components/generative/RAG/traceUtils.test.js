import {
  collectTraceStats,
  computeDiscardedRefs,
  filterRenderableEntries,
  findRerankNode,
  isQueryTransformed,
} from "./traceUtils";

const queryEntry = (query, chunks) => ({
  query,
  retriever: { name: "Dense", chunks },
});
const rerankEntry = {
  stage: "rerank",
  reranker: { name: "Dense", chunks: ["1_0"], pool: ["1_0", "1_1"] },
};

describe("findRerankNode", () => {
  it("returns the reranker node of the rerank entry", () => {
    const trace = [queryEntry("a", ["1_0"]), rerankEntry];
    expect(findRerankNode(trace)).toBe(rerankEntry.reranker);
  });

  it("returns null without a rerank entry or with a bad trace", () => {
    expect(findRerankNode([queryEntry("a", ["1_0"])])).toBeNull();
    expect(findRerankNode(null)).toBeNull();
    expect(findRerankNode([{ stage: "rerank", reranker: "x" }])).toBeNull();
  });
});

describe("rerank entry does not affect the per-query derivations", () => {
  const trace = [
    queryEntry("a", ["1_0", "1_1"]),
    queryEntry("b", ["1_1"]),
    rerankEntry,
  ];

  it("is excluded from the renderable entries", () => {
    expect(filterRenderableEntries(trace)).toHaveLength(2);
  });

  it("keeps the query count and candidate stats", () => {
    const entries = filterRenderableEntries(trace);
    expect(isQueryTransformed(entries, "msg")).toBe(true);
    expect(collectTraceStats(entries).candidates).toEqual(["1_0", "1_1"]);
  });

  it("still counts candidates the reranker dropped as discarded", () => {
    const entries = filterRenderableEntries(trace);
    expect(computeDiscardedRefs(entries, { "1_0": {} })).toEqual(["1_1"]);
  });
});
