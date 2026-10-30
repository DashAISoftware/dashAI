import {
  buildSplitsPayload,
  defaultSplitterOf,
  metricsByPartition,
  splittersOf,
  SPLIT_TYPES,
  STRATEGY_KINDS,
} from "./splitsPayload";

/*
 * The splits payload the session wizard stores, the splitters a strategy
 * takes, and the metric lists sent per partition when the session is created.
 *
 * splitsOf repeats what PrepareDatasetStep.updateExperiment passes to
 * buildSplitsPayload. Which partitions receive rows is the splitter's preview
 * to say (POST /splitter/preview, on the shared splitPreviewCases.json); the
 * wizard only turns them into metric lists.
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

const TEMPORAL = {
  name: "TemporalHoldoutSplitter",
  metadata: { partitioning: "holdout", geometry: "partitions" },
  schema: { properties: {} },
};
const ROLLING = {
  name: "RollingOriginSplitter",
  metadata: { partitioning: "origins", geometry: "backtest_origins" },
  schema: { properties: { horizon: {}, n_origins: {} } },
};

const EMPTY_INDEXES = { train: [], validation: [], test: [] };

const splitsOf = ({
  strategyKind,
  splitType,
  splitterParams = null,
  splitter = null,
  groupColumn = "",
  datasetPartitionsIndex = {},
  rowsPartitionsIndex = EMPTY_INDEXES,
}) => {
  const splitterName =
    strategyKind && strategyKind !== STRATEGY_KINDS.FULL
      ? splitter?.name
      : null;
  if (!splitterName) return {};
  const splitTypeOf = {
    [STRATEGY_KINDS.HOLDOUT]: splitType,
    [STRATEGY_KINDS.CV]: SPLIT_TYPES.CV,
  };
  return buildSplitsPayload({
    splitterName,
    splitType: splitTypeOf[strategyKind],
    params: {
      ...(splitterParams ?? {}),
      ...(splitter?.schema?.properties?.group_column
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
      splitter: HOLDOUT,
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
      splitter: HOLDOUT,
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
      splitter: HOLDOUT,
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
      splitter: HOLDOUT,
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
      splitter: KFOLD,
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
      splitter: KFOLD,
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
      splitter: KFOLD,
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
        splitter: GROUP_KFOLD,
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
        splitter: GROUP_KFOLD,
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
      splitter: KFOLD,
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
        splitter: KFOLD,
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
        splitter: HOLDOUT,
      }),
    ).toEqual({ splitter_name: "HoldoutSplitter", splitType: "random" });
  });
});

it("any other strategy: the splitter's parameters alone, with no split type", () => {
  expect(
    JSON.parse(
      JSON.stringify(
        splitsOf({
          strategyKind: "backtest",
          splitType: SPLIT_TYPES.RANDOM,
          splitter: ROLLING,
          splitterParams: { horizon: 3, n_origins: 4 },
        }),
      ),
    ),
  ).toEqual({
    splitter_name: "RollingOriginSplitter",
    horizon: 3,
    n_origins: 4,
  });
});

describe("the splitters a strategy takes", () => {
  const SPLITTERS = [TEMPORAL, HOLDOUT, KFOLD, GROUP_KFOLD, ROLLING];
  const strategy = (splitter_partitioning, default_splitter = null) => ({
    metadata: { splitter_partitioning, default_splitter },
  });

  it("are the ones that carve the way the strategy declares, in order", () => {
    expect(splittersOf(strategy("holdout"), SPLITTERS)).toEqual([
      TEMPORAL,
      HOLDOUT,
    ]);
    expect(splittersOf(strategy("folds"), SPLITTERS)).toEqual([
      KFOLD,
      GROUP_KFOLD,
    ]);
    expect(splittersOf(strategy("origins"), SPLITTERS)).toEqual([ROLLING]);
    expect(splittersOf(strategy(null), SPLITTERS)).toEqual([]);
    expect(splittersOf(null, SPLITTERS)).toEqual([]);
  });

  it("start on the one the strategy declares, else on the first", () => {
    expect(
      defaultSplitterOf(strategy("holdout", "HoldoutSplitter"), [
        TEMPORAL,
        HOLDOUT,
      ]),
    ).toBe(HOLDOUT);
    expect(defaultSplitterOf(strategy("folds"), [KFOLD, GROUP_KFOLD])).toBe(
      KFOLD,
    );
    // A default the task does not offer falls back to the first.
    expect(
      defaultSplitterOf(strategy("holdout", "HoldoutSplitter"), [TEMPORAL]),
    ).toBe(TEMPORAL);
    expect(defaultSplitterOf(strategy("holdout"), [])).toBeNull();
  });
});

describe("metric lists CreateSessionSteps sends per partition", () => {
  const ALL_METRICS = ["Accuracy", "F1", "Precision"];

  it("every metric on each partition with rows, none on the others", () => {
    expect(metricsByPartition(["train", "test"], ALL_METRICS)).toEqual({
      train: ALL_METRICS,
      validation: [],
      test: ALL_METRICS,
    });
    expect(metricsByPartition(["validation", "test"], ALL_METRICS)).toEqual({
      train: [],
      validation: ALL_METRICS,
      test: ALL_METRICS,
    });
  });

  it("no partitions known (full strategy): no metrics on any partition", () => {
    expect(metricsByPartition(null, ALL_METRICS)).toEqual({
      train: [],
      validation: [],
      test: [],
    });
  });

  it("metrics fetch failed: every list is empty whatever the partitions", () => {
    expect(metricsByPartition(["train", "validation", "test"], [])).toEqual({
      train: [],
      validation: [],
      test: [],
    });
  });
});
