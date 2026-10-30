import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { previewSplit } from "../api/splitter";
import useSplitPreview from "./useSplitPreview";

jest.mock("../api/splitter", () => ({ previewSplit: jest.fn() }));

function Probe(request) {
  const { preview, loading } = useSplitPreview(request);
  return (
    <div data-testid="probe">
      {loading ? "loading" : JSON.stringify(preview?.partitions ?? null)}
    </div>
  );
}

const answer = (partitions) => ({
  rows: [],
  notes: [],
  shares: {},
  errors: [],
  partitions,
});

const deferred = () => {
  let resolve;
  const promise = new Promise((done) => {
    resolve = done;
  });
  return { promise, resolve };
};

describe("useSplitPreview", () => {
  it("asks the splitter, and returns nothing while the request is pending", async () => {
    const pending = deferred();
    previewSplit.mockReturnValueOnce(pending.promise);

    render(
      <Probe
        datasetId={1}
        splitterName="HoldoutSplitter"
        params={{ train: 1 }}
      />,
    );
    expect(screen.getByTestId("probe").textContent).toBe("loading");

    await waitFor(() => expect(previewSplit).toHaveBeenCalledTimes(1));
    expect(previewSplit).toHaveBeenCalledWith({
      datasetId: 1,
      splitterName: "HoldoutSplitter",
      params: { train: 1 },
      splitType: null,
      indexes: null,
    });
    pending.resolve(answer(["train"]));
    await waitFor(() =>
      expect(screen.getByTestId("probe").textContent).toBe('["train"]'),
    );
  });

  it("never takes an older answer for the current configuration", async () => {
    const older = deferred();
    const newer = deferred();
    previewSplit
      .mockReturnValueOnce(older.promise)
      .mockReturnValueOnce(newer.promise);

    const { rerender } = render(
      <Probe datasetId={1} splitterName="KFoldSplitter" params={{ n: 1 }} />,
    );
    await waitFor(() => expect(previewSplit).toHaveBeenCalledTimes(1));

    rerender(
      <Probe datasetId={1} splitterName="KFoldSplitter" params={{ n: 2 }} />,
    );
    await waitFor(() => expect(previewSplit).toHaveBeenCalledTimes(2));

    older.resolve(answer(["old"]));
    await new Promise((done) => setTimeout(done, 50));
    expect(screen.getByTestId("probe").textContent).toBe("loading");

    newer.resolve(answer(["new"]));
    await waitFor(() =>
      expect(screen.getByTestId("probe").textContent).toBe('["new"]'),
    );
  });

  it("asks nothing without a splitter", async () => {
    render(<Probe datasetId={1} splitterName={null} params={{}} />);

    await new Promise((done) => setTimeout(done, 400));
    expect(previewSplit).not.toHaveBeenCalled();
    expect(screen.getByTestId("probe").textContent).toBe("null");
  });
});
