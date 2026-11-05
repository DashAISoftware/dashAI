import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { previewSplit } from "../api/splitter";
import useSplitPreview, { SPLIT_PREVIEW_TIMEOUT_MS } from "./useSplitPreview";

jest.mock("../api/splitter", () => ({ previewSplit: jest.fn() }));

function Probe(request) {
  const { preview, loading, error, errorStatus, retry } =
    useSplitPreview(request);
  return (
    <>
      <div data-testid="probe">
        {loading ? "loading" : JSON.stringify(preview?.partitions ?? null)}
      </div>
      <div data-testid="error">{JSON.stringify({ error, errorStatus })}</div>
      <button type="button" onClick={retry}>
        retry
      </button>
    </>
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
    expect(previewSplit).toHaveBeenCalledWith(
      {
        datasetId: 1,
        splitterName: "HoldoutSplitter",
        params: { train: 1 },
        splitType: null,
        indexes: null,
      },
      expect.objectContaining({ timeout: SPLIT_PREVIEW_TIMEOUT_MS }),
    );
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

  it("aborts a request a newer one supersedes, and gives up on one that never answers", async () => {
    previewSplit.mockImplementation(() => new Promise(() => {}));

    const { rerender } = render(
      <Probe datasetId={1} splitterName="KFoldSplitter" params={{ n: 1 }} />,
    );
    await waitFor(() => expect(previewSplit).toHaveBeenCalledTimes(1));
    const [, first] = previewSplit.mock.calls[0];
    expect(first.timeout).toBe(SPLIT_PREVIEW_TIMEOUT_MS);
    expect(first.signal.aborted).toBe(false);

    rerender(
      <Probe datasetId={1} splitterName="KFoldSplitter" params={{ n: 2 }} />,
    );
    await waitFor(() => expect(previewSplit).toHaveBeenCalledTimes(2));

    expect(first.signal.aborted).toBe(true);
    expect(previewSplit.mock.calls[1][1].signal.aborted).toBe(false);
  });

  it("reports a failed request with the backend's reason and status, and asks again on retry", async () => {
    previewSplit.mockRejectedValueOnce({
      message: "Request failed with status code 422",
      response: { status: 422, data: { detail: "n_origins: too small" } },
    });
    previewSplit.mockResolvedValueOnce(answer(["validation", "test"]));

    render(
      <Probe
        datasetId={1}
        splitterName="RollingOriginSplitter"
        params={{ n_origins: 0 }}
      />,
    );

    await waitFor(() =>
      expect(JSON.parse(screen.getByTestId("error").textContent)).toEqual({
        error: "n_origins: too small",
        errorStatus: 422,
      }),
    );
    expect(screen.getByTestId("probe").textContent).toBe("null");

    fireEvent.click(screen.getByRole("button", { name: "retry" }));

    expect(screen.getByTestId("probe").textContent).toBe("loading");
    await waitFor(() =>
      expect(screen.getByTestId("probe").textContent).toBe(
        '["validation","test"]',
      ),
    );
    expect(previewSplit).toHaveBeenCalledTimes(2);
    expect(JSON.parse(screen.getByTestId("error").textContent)).toEqual({
      error: null,
      errorStatus: null,
    });
  });

  it("reports a request that got no answer without a status", async () => {
    previewSplit.mockRejectedValueOnce({ message: "timeout of 20000ms" });

    render(
      <Probe datasetId={1} splitterName="KFoldSplitter" params={{ n: 1 }} />,
    );

    await waitFor(() =>
      expect(JSON.parse(screen.getByTestId("error").textContent)).toEqual({
        error: "timeout of 20000ms",
        errorStatus: null,
      }),
    );
  });
});
