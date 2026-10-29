import { buildSplitPreview } from "./splitPreview";
import { buildSplitsPayload, hasPartition } from "./splitsPayload";
import splitPreviewCases from "../components/models/modelSession/__fixtures__/splitPreviewCases.json";

/*
 * The net of the split preview, before the backend computes it.
 *
 * Every case records three things the wizard derived on its own from a
 * splitter configuration: the drawing (rows, notes, shares), the problems that
 * keep Next disabled (errors) and the partitions that receive rows, which pick
 * the metric lists sent when the session is created. The backend runs the same
 * cases and has to answer the same.
 *
 * Record with RECORD_SPLIT_PREVIEW_CASES=1, which rewrites the expectations of
 * the fixture from the code under test.
 */

const RECORDING = process.env.RECORD_SPLIT_PREVIEW_CASES === "1";
const LABEL_PREFIX = "experiments:splitPreview.";
const PARTITIONS = ["train", "validation", "test"];

// The labels name a translation; the cases keep only what is after the
// namespace, so the backend can answer them without knowing where the
// frontend keeps its texts.
const neutralRows = (rows) =>
  rows.map((row) =>
    row.ellipsis
      ? { key: row.key, ellipsis: true, hidden_count: row.hiddenCount }
      : {
          key: row.key,
          label: row.labelKey.replace(LABEL_PREFIX, ""),
          label_values: row.labelValues ?? {},
          segments: row.segments,
        },
  );

const previewOf = (c) => {
  const preview = buildSplitPreview({
    geometry: c.geometry,
    splitType: c.split_type,
    params: c.params,
    indexes: c.indexes,
    datasetInfo: c.dataset,
  });
  return {
    rows: neutralRows(preview.rows),
    notes: preview.notes,
    shares: preview.shares,
  };
};

const partitionsOf = (c) => {
  const payload = buildSplitsPayload({
    splitterName: "Splitter",
    splitType: c.split_type,
    params: c.params,
    indexes: c.indexes,
  });
  return PARTITIONS.filter((partition) => hasPartition(payload, partition));
};

// What SplitDatasetRows checks before enabling Next, transcribed from the
// component. Only the recording reads it: the component test checks that the
// component shows these same messages on the same cases.
const errorsOf = (c) => {
  const { params, indexes, dataset } = c;
  if (c.split_type === "random") {
    const numbers = ["train", "validation", "test"].every(
      (key) => typeof params[key] === "number",
    );
    if (params.train === 0) {
      return [{ key: "trainSplitMustBeGreaterThanZero", values: {} }];
    }
    const sum = params.train + params.validation + params.test;
    if (numbers && Math.abs(sum - 1) >= 0.0001) {
      return [{ key: "splitsMustSumToOne", values: {} }];
    }
    return [];
  }
  if (c.split_type === "manual") {
    return indexes.train.length === 0
      ? [{ key: "trainSplitMustHaveAtLeastOneRow", values: {} }]
      : [];
  }
  if (c.split_type === "cv") {
    const folds = params.n_splits;
    return typeof folds === "number" && folds > (dataset.total_rows ?? 0)
      ? [
          {
            key: "foldsMustBeLessThanDatasetSize",
            values: { datasetSize: dataset.total_rows },
          },
        ]
      : [];
  }
  return [];
};

if (RECORDING) {
  // eslint-disable-next-line global-require
  const fs = require("fs");
  // eslint-disable-next-line global-require
  const path = require("path");

  it("records the expectations of the shared split preview cases", () => {
    const recorded = splitPreviewCases.map((c) => {
      const { expected: _previous, ...input } = c;
      return {
        ...input,
        expected: {
          ...previewOf(c),
          errors: errorsOf(c),
          partitions: partitionsOf(c),
        },
      };
    });
    fs.writeFileSync(
      path.join(
        __dirname,
        "../components/models/modelSession/__fixtures__/splitPreviewCases.json",
      ),
      JSON.stringify(recorded, null, 2) + "\n",
    );
  });
} else {
  describe("the split preview, on the cases the backend runs too", () => {
    it.each(splitPreviewCases.map((c) => [c.name, c]))("%s", (_name, c) => {
      const preview = previewOf(c);
      expect(preview.rows).toEqual(c.expected.rows);
      expect(preview.notes).toEqual(c.expected.notes);
      expect(preview.shares).toEqual(c.expected.shares);
    });
  });

  describe("the partitions with rows, on the same cases", () => {
    it.each(splitPreviewCases.map((c) => [c.name, c]))("%s", (_name, c) => {
      expect(partitionsOf(c)).toEqual(c.expected.partitions);
    });
  });
}
