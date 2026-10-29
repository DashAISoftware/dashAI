import {
  buildSplitsPayload,
  hasPartition,
  resolveSplitterName,
  SPLIT_TYPES,
  STRATEGY_KINDS,
} from "./splitsPayload";

/*
 * The splits payload the session wizard stores, and the metric lists sent per
 * partition when the session is created, pinned before the partitions with
 * rows are decided by the backend.
 *
 * splitsOf repeats what PrepareDatasetStep.updateExperiment passes to
 * buildSplitsPayload, and metricListsOf what CreateSessionSteps.createSession
 * sends to createModelSession for each partition.
 */

const HOLDOUT = {
  name: "HoldoutSplitter",
  metadata: { partitioning: "holdout", geometry: "partitions" },
  schema: { properties: {} },
};
const KFOLD = {
  name: "KFoldSplitter",
  metadata: { partitioning: "folds", geometry: "blocked_folds" },
  schema: { properties: { n_splits: {}, test_size: {} } },
};
const GROUP_KFOLD = {
  name: "GroupKFoldSplitter",
  metadata: { partitioning: "folds", geometry: "blocked_folds" },
  schema: { properties: { n_splits: {}, group_column: {} } },
};

const EMPTY_INDEXES = { train: [], validation: [], test: [] };

const splitsOf = ({
  strategyKind,
  splitType,
  splitterParams = null,
  cvType = null,
  holdoutType = null,
  groupColumn = "",
  datasetPartitionsIndex = {},
  rowsPartitionsIndex = EMPTY_INDEXES,
}) => {
  const splitterName = resolveSplitterName(strategyKind, cvType, holdoutType);
  if (!splitterName) return {};
  return buildSplitsPayload({
    splitterName,
    splitType:
      strategyKind === STRATEGY_KINDS.HOLDOUT ? splitType : SPLIT_TYPES.CV,
    params: {
      ...(splitterParams ?? {}),
      ...(cvType?.schema?.properties?.group_column
        ? { group_column: groupColumn }
        : {}),
    },
    indexes:
      splitType === SPLIT_TYPES.PREDEFINED
        ? datasetPartitionsIndex
        : rowsPartitionsIndex,
  });
};

const ALL_METRICS = ["Accuracy", "F1", "Precision"];

const metricListsOf = (splits, allMetricNames = ALL_METRICS) => ({
  train: hasPartition(splits, "train") ? allMetricNames : [],
  validation: hasPartition(splits, "validation") ? allMetricNames : [],
  test: hasPartition(splits, "test") ? allMetricNames : [],
});

describe("splits payload written by PrepareDatasetStep", () => {
  it("holdout random: keeps the proportions and every other form value, with no indexes", () => {
    const splits = splitsOf({
      strategyKind: STRATEGY_KINDS.HOLDOUT,
      splitType: SPLIT_TYPES.RANDOM,
      holdoutType: HOLDOUT,
      splitterParams: {
        train: 0.6,
        validation: 0.2,
        test: 0.2,
        shuffle: true,
        stratify: false,
        random_state: 42,
      },
      rowsPartitionsIndex: { train: [0], validation: [], test: [] },
    });

    expect(splits).toEqual({
      splitter_name: "HoldoutSplitter",
      splitType: "random",
      train: 0.6,
      validation: 0.2,
      test: 0.2,
      shuffle: true,
      stratify: false,
      random_state: 42,
    });
  });

  it("holdout random: drops parameters the form left undefined", () => {
    const splits = splitsOf({
      strategyKind: STRATEGY_KINDS.HOLDOUT,
      splitType: SPLIT_TYPES.RANDOM,
      holdoutType: HOLDOUT,
      splitterParams: { train: 0.7, validation: 0, test: 0.3, seed: undefined },
    });

    expect(splits).toEqual({
      splitter_name: "HoldoutSplitter",
      splitType: "random",
      train: 0.7,
      validation: 0,
      test: 0.3,
    });
  });

  it("holdout manual: drops the proportions and carries the typed row indexes", () => {
    const splits = splitsOf({
      strategyKind: STRATEGY_KINDS.HOLDOUT,
      splitType: SPLIT_TYPES.MANUAL,
      holdoutType: HOLDOUT,
      splitterParams: { train: 0.6, validation: 0.2, test: 0.2, shuffle: true },
      datasetPartitionsIndex: { train: [9], validation: [], test: [] },
      rowsPartitionsIndex: {
        train: [0, 1, 2, 3, 4, 5],
        validation: [6, 7],
        test: [8, 9],
      },
    });

    expect(splits).toEqual({
      splitter_name: "HoldoutSplitter",
      splitType: "manual",
      shuffle: true,
      splitted_indexes: {
        train_indexes: [0, 1, 2, 3, 4, 5],
        test_indexes: [8, 9],
        val_indexes: [6, 7],
      },
    });
  });

  it("holdout predefined: carries the dataset's own partition indexes, not the typed ones", () => {
    const splits = splitsOf({
      strategyKind: STRATEGY_KINDS.HOLDOUT,
      splitType: SPLIT_TYPES.PREDEFINED,
      holdoutType: HOLDOUT,
      splitterParams: { train: 0.6, validation: 0.2, test: 0.2 },
      datasetPartitionsIndex: {
        train: [0, 1, 2, 3, 4, 5, 6],
        validation: [],
        test: [7, 8, 9],
      },
      rowsPartitionsIndex: { train: [0], validation: [], test: [] },
    });

    expect(splits).toEqual({
      splitter_name: "HoldoutSplitter",
      splitType: "predefined",
      splitted_indexes: {
        train_indexes: [0, 1, 2, 3, 4, 5, 6],
        test_indexes: [7, 8, 9],
        val_indexes: [],
      },
    });
  });

  it("cv without test_size: splitType is cv whatever the holdout split type was, and carries no indexes", () => {
    const splits = splitsOf({
      strategyKind: STRATEGY_KINDS.CV,
      splitType: SPLIT_TYPES.RANDOM,
      cvType: KFOLD,
      holdoutType: HOLDOUT,
      splitterParams: { n_splits: 5, shuffle: true, random_state: 0 },
    });

    expect(splits).toEqual({
      splitter_name: "KFoldSplitter",
      splitType: "cv",
      n_splits: 5,
      shuffle: true,
      random_state: 0,
    });
  });

  it("cv with test_size: keeps test_size at the top level", () => {
    const splits = splitsOf({
      strategyKind: STRATEGY_KINDS.CV,
      splitType: SPLIT_TYPES.RANDOM,
      cvType: KFOLD,
      splitterParams: { n_splits: 5, test_size: 0.2 },
    });

    expect(splits).toEqual({
      splitter_name: "KFoldSplitter",
      splitType: "cv",
      n_splits: 5,
      test_size: 0.2,
    });
  });

  it("cv after a predefined holdout: splitType is cv but the predefined indexes are not sent", () => {
    const splits = splitsOf({
      strategyKind: STRATEGY_KINDS.CV,
      splitType: SPLIT_TYPES.PREDEFINED,
      cvType: KFOLD,
      splitterParams: { n_splits: 3 },
      datasetPartitionsIndex: { train: [0], validation: [], test: [1] },
    });

    expect(splits).toEqual({
      splitter_name: "KFoldSplitter",
      splitType: "cv",
      n_splits: 3,
    });
  });

  it("cv with a grouping splitter: adds group_column from the hand rendered select, even when empty", () => {
    expect(
      splitsOf({
        strategyKind: STRATEGY_KINDS.CV,
        splitType: SPLIT_TYPES.RANDOM,
        cvType: GROUP_KFOLD,
        splitterParams: { n_splits: 4 },
        groupColumn: "patient",
      }),
    ).toEqual({
      splitter_name: "GroupKFoldSplitter",
      splitType: "cv",
      n_splits: 4,
      group_column: "patient",
    });

    expect(
      splitsOf({
        strategyKind: STRATEGY_KINDS.CV,
        splitType: SPLIT_TYPES.RANDOM,
        cvType: GROUP_KFOLD,
        splitterParams: { n_splits: 4 },
      }),
    ).toEqual({
      splitter_name: "GroupKFoldSplitter",
      splitType: "cv",
      n_splits: 4,
      group_column: "",
    });
  });

  it("cv with a splitter without group_column: never adds group_column", () => {
    const splits = splitsOf({
      strategyKind: STRATEGY_KINDS.CV,
      splitType: SPLIT_TYPES.RANDOM,
      cvType: KFOLD,
      splitterParams: { n_splits: 5 },
      groupColumn: "patient",
    });

    expect(splits).not.toHaveProperty("group_column");
  });

  it("no splitter resolved (full strategy, or none chosen yet): leaves the empty splits untouched", () => {
    expect(
      splitsOf({
        strategyKind: STRATEGY_KINDS.FULL,
        splitType: SPLIT_TYPES.RANDOM,
        cvType: KFOLD,
        holdoutType: HOLDOUT,
      }),
    ).toEqual({});
    expect(
      splitsOf({ strategyKind: STRATEGY_KINDS.HOLDOUT, splitType: "random" }),
    ).toEqual({});
    expect(
      splitsOf({ strategyKind: STRATEGY_KINDS.CV, splitType: "random" }),
    ).toEqual({});
  });

  it("holdout with no parameter submitted yet: only the meta keys", () => {
    expect(
      splitsOf({
        strategyKind: STRATEGY_KINDS.HOLDOUT,
        splitType: SPLIT_TYPES.RANDOM,
        holdoutType: HOLDOUT,
      }),
    ).toEqual({ splitter_name: "HoldoutSplitter", splitType: "random" });
  });
});

describe("metric lists CreateSessionSteps sends per partition", () => {
  const holdoutRandom = (train, validation, test) =>
    splitsOf({
      strategyKind: STRATEGY_KINDS.HOLDOUT,
      splitType: SPLIT_TYPES.RANDOM,
      holdoutType: HOLDOUT,
      splitterParams: { train, validation, test },
    });
  const holdoutManual = (rowsPartitionsIndex) =>
    splitsOf({
      strategyKind: STRATEGY_KINDS.HOLDOUT,
      splitType: SPLIT_TYPES.MANUAL,
      holdoutType: HOLDOUT,
      splitterParams: { train: 0.6, validation: 0.2, test: 0.2 },
      rowsPartitionsIndex,
    });
  const holdoutPredefined = (datasetPartitionsIndex) =>
    splitsOf({
      strategyKind: STRATEGY_KINDS.HOLDOUT,
      splitType: SPLIT_TYPES.PREDEFINED,
      holdoutType: HOLDOUT,
      datasetPartitionsIndex,
    });
  const cv = (splitterParams) =>
    splitsOf({
      strategyKind: STRATEGY_KINDS.CV,
      splitType: SPLIT_TYPES.RANDOM,
      cvType: KFOLD,
      splitterParams,
    });

  it("holdout random with three non zero proportions: metrics on train, validation and test", () => {
    expect(metricListsOf(holdoutRandom(0.6, 0.2, 0.2))).toEqual({
      train: ALL_METRICS,
      validation: ALL_METRICS,
      test: ALL_METRICS,
    });
  });

  it("holdout random with validation 0: no validation metrics", () => {
    expect(metricListsOf(holdoutRandom(0.7, 0, 0.3))).toEqual({
      train: ALL_METRICS,
      validation: [],
      test: ALL_METRICS,
    });
  });

  it("holdout random with train 0: no train metrics", () => {
    expect(metricListsOf(holdoutRandom(0, 0.5, 0.5))).toEqual({
      train: [],
      validation: ALL_METRICS,
      test: ALL_METRICS,
    });
  });

  it("holdout random with no proportion submitted: no metrics on any partition", () => {
    expect(
      metricListsOf(
        splitsOf({
          strategyKind: STRATEGY_KINDS.HOLDOUT,
          splitType: SPLIT_TYPES.RANDOM,
          holdoutType: HOLDOUT,
        }),
      ),
    ).toEqual({ train: [], validation: [], test: [] });
  });

  it("holdout manual: metrics only on the partitions given rows", () => {
    expect(
      metricListsOf(
        holdoutManual({ train: [0, 1, 2], validation: [], test: [3, 4] }),
      ),
    ).toEqual({ train: ALL_METRICS, validation: [], test: ALL_METRICS });
    expect(
      metricListsOf(
        holdoutManual({ train: [0, 1], validation: [2], test: [3] }),
      ),
    ).toEqual({
      train: ALL_METRICS,
      validation: ALL_METRICS,
      test: ALL_METRICS,
    });
  });

  it("holdout manual: the proportions the form still holds do not count", () => {
    expect(
      metricListsOf(holdoutManual({ train: [0, 1], validation: [], test: [] })),
    ).toEqual({ train: ALL_METRICS, validation: [], test: [] });
  });

  it("holdout predefined: metrics only on the dataset's non empty partitions", () => {
    expect(
      metricListsOf(
        holdoutPredefined({ train: [0, 1, 2], validation: [], test: [3] }),
      ),
    ).toEqual({ train: ALL_METRICS, validation: [], test: ALL_METRICS });
  });

  it("cv without test_size: metrics on train and validation, none on test", () => {
    expect(metricListsOf(cv({ n_splits: 5 }))).toEqual({
      train: ALL_METRICS,
      validation: ALL_METRICS,
      test: [],
    });
    expect(metricListsOf(cv({ n_splits: 5, test_size: 0 }))).toEqual({
      train: ALL_METRICS,
      validation: ALL_METRICS,
      test: [],
    });
  });

  it("cv with test_size: metrics on train, validation and test", () => {
    expect(metricListsOf(cv({ n_splits: 5, test_size: 0.2 }))).toEqual({
      train: ALL_METRICS,
      validation: ALL_METRICS,
      test: ALL_METRICS,
    });
  });

  it("cv stored with the old holdout key: test metrics when holdout > 0", () => {
    expect(
      metricListsOf({
        splitter_name: "KFoldSplitter",
        splitType: "cv",
        n_splits: 5,
        holdout: 0.1,
      }),
    ).toEqual({
      train: ALL_METRICS,
      validation: ALL_METRICS,
      test: ALL_METRICS,
    });
  });

  it("empty splits (full strategy): no metrics on any partition", () => {
    expect(metricListsOf({})).toEqual({ train: [], validation: [], test: [] });
    expect(metricListsOf(undefined)).toEqual({
      train: [],
      validation: [],
      test: [],
    });
  });

  it("metrics fetch failed: every list is empty whatever the partitions", () => {
    expect(metricListsOf(holdoutRandom(0.6, 0.2, 0.2), [])).toEqual({
      train: [],
      validation: [],
      test: [],
    });
  });

  it("legacy payloads with indexes under the partition names", () => {
    expect(
      metricListsOf({
        splitType: "manual",
        train: [0, 1],
        validation: [],
        test: [2],
      }),
    ).toEqual({ train: ALL_METRICS, validation: [], test: ALL_METRICS });
  });
});
