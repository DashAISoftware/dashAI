import React, { useCallback, useState } from "react";
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { renderWithProviders } from "../../../test-utils/renderWithProviders";
import i18n from "../../../utils/i18n";
import { getComponents } from "../../../api/component";
import { previewSplit } from "../../../api/splitter";
import { parseIndexToRange } from "../../../utils/parseRange";
import { SPLIT_TYPES } from "../../../utils/splitsPayload";
import splitPreviewCases from "./__fixtures__/splitPreviewCases.json";
import SplitDatasetRows from "./SplitDatasetRows";

/*
 * The splits step of the session wizard. The splitter computes the preview on
 * the backend (POST /splitter/preview), and with it whether the configuration
 * can be used and which partitions receive rows; tests/back/splitters/
 * test_split_preview.py checks the backend answers the shared cases with their
 * `expected`. Here the cases pin the request the step sends, which messages it
 * shows and whether it lets the wizard go on.
 */

jest.mock("react-markdown", () => ({
  __esModule: true,
  default: ({ children }) => <span>{children}</span>,
}));

jest.mock("notistack", () => {
  const snackbar = { enqueueSnackbar: jest.fn(), closeSnackbar: jest.fn() };
  return { useSnackbar: () => snackbar };
});

jest.mock("../../../api/component", () => ({ getComponents: jest.fn() }));

jest.mock("../../../api/splitter", () => ({ previewSplit: jest.fn() }));

// What the stub form submits on mount. Undefined means it submits nothing,
// which is what the generated form does until the user edits a field.
let mockFormParams;

jest.mock("../../shared/FormSchema", () => {
  const ReactInStub = require("react");
  function FormSchemaStub(props) {
    ReactInStub.useEffect(() => {
      if (mockFormParams !== undefined) props.onFormSubmit(mockFormParams);
    }, []);
    return (
      <div
        data-testid={`form-schema-${props.model}`}
        data-excluded={JSON.stringify(props.excludeFields)}
      />
    );
  }
  return { __esModule: true, default: FormSchemaStub };
});

jest.mock("./SplitPreview", () => ({
  __esModule: true,
  default: ({ preview, loading, failure, onRetry }) => (
    <div
      data-testid="split-preview"
      data-preview={JSON.stringify(preview ?? null)}
      data-loading={String(loading)}
      data-failure={JSON.stringify(failure ?? null)}
    >
      <button type="button" onClick={onRetry}>
        retry-preview
      </button>
    </div>
  ),
}));

const HOLDOUT_STRATEGY = {
  name: "HoldoutEvaluationStrategy",
  display_name: "Holdout",
  type: "EvaluationStrategy",
  metadata: {
    kind: "holdout",
    scored_splits: ["train", "validation", "test"],
    splitter_partitioning: "holdout",
    default_splitter: "HoldoutSplitter",
    result_views: [],
  },
};
const CV_STRATEGY = {
  name: "CrossValidationEvaluationStrategy",
  display_name: "Cross-Validation",
  type: "EvaluationStrategy",
  metadata: {
    kind: "cv",
    scored_splits: ["train", "validation", "test"],
    splitter_partitioning: "folds",
    default_splitter: null,
    result_views: ["fold_metrics"],
  },
};
// A strategy of a kind the step has no section of its own for.
const BACKTEST_STRATEGY = {
  name: "ForecastingCrossValidationEvaluationStrategy",
  display_name: "Rolling origin",
  type: "EvaluationStrategy",
  metadata: {
    kind: "backtest",
    scored_splits: ["validation", "test"],
    splitter_partitioning: "origins",
    default_splitter: "RollingOriginSplitter",
    result_views: ["fold_metrics", "forecasts"],
  },
};

const splitter = (name, displayName, metadata, properties = {}) => ({
  name,
  display_name: displayName,
  type: "Splitter",
  metadata,
  schema: { properties },
});

// Listed before HoldoutSplitter on purpose: the default holdout splitter is
// the one the strategy declares, not the first one listed.
const TEMPORAL_HOLDOUT = splitter("TemporalHoldoutSplitter", "Temporal", {
  partitioning: "holdout",
  geometry: "partitions",
});
const HOLDOUT = splitter("HoldoutSplitter", "Holdout", {
  partitioning: "holdout",
  geometry: "partitions",
});
const KFOLD = splitter("KFoldSplitter", "K-Fold", {
  partitioning: "folds",
  geometry: "blocked_folds",
});
const STRATIFIED_KFOLD = splitter("StratifiedKFoldSplitter", "Stratified", {
  partitioning: "folds",
  geometry: "blocked_folds",
});
const GROUP_KFOLD = splitter(
  "GroupKFoldSplitter",
  "Group K-Fold",
  { partitioning: "folds", geometry: "blocked_folds" },
  { group_column: { type: "string" }, n_splits: { type: "integer" } },
);
// The origin splitters of a forecasting task. The temporal holdout is listed
// first, so the declared default is not merely the first one.
const ORIGIN_TEMPORAL_HOLDOUT = splitter(
  "TemporalHoldoutSplitter",
  "Temporal holdout",
  { partitioning: "origins", geometry: "backtest_origins" },
);
const ROLLING_ORIGIN = splitter("RollingOriginSplitter", "Rolling origin", {
  partitioning: "origins",
  geometry: "backtest_origins",
});

const SPLITTERS = [
  TEMPORAL_HOLDOUT,
  HOLDOUT,
  KFOLD,
  STRATIFIED_KFOLD,
  GROUP_KFOLD,
];
const STRATEGIES = [HOLDOUT_STRATEGY, CV_STRATEGY];

// What getComponents({ model }) answers, by splitter name. By default the
// schemas carry no placeholder, so nothing is seeded over the stub's values.
let mockSchemasByName = {};

const mockComponents = ({ splitters = SPLITTERS, strategies = STRATEGIES }) =>
  getComponents.mockImplementation(async (args) => {
    if (args.model) {
      return mockSchemasByName[args.model] ?? { schema: { properties: {} } };
    }
    if (args.selectTypes?.[0] === "Splitter") return splitters;
    if (args.selectTypes?.[0] === "EvaluationStrategy") return strategies;
    return [];
  });

// A preview the backend could answer for a usable configuration.
const previewAnswer = ({
  errors = [],
  partitions = ["train", "validation", "test"],
} = {}) => ({
  rows: [],
  notes: [],
  shares: {},
  errors,
  partitions,
});

const DATASET_ID = 7;

const NO_PREDEFINED = {
  total_rows: 150,
  train_size: 0,
  val_size: 0,
  test_size: 0,
};
const PREDEFINED = { total_rows: 10, train_size: 7, val_size: 0, test_size: 3 };

// Owns the state PrepareDatasetStep owns, wired the same way.
let harness;
const spies = {};

function Harness({ datasetInfo, taskName, inputColumnNames }) {
  const [splitterParams, setSplitterParams] = useState(null);
  const [paramsError, setParamsError] = useState(false);
  const [splitter, setSplitterState] = useState(null);
  const [splitPartitions, setSplitPartitionsState] = useState(null);
  const [strategyKind, setStrategyKind] = useState(null);
  const [groupColumn, setGroupColumn] = useState("");
  const [rowsPartitionsIndex, setRowsPartitionsIndex] = useState({
    train: [],
    validation: [],
    test: [],
  });
  const [splitType, setSplitType] = useState("");
  const [evaluationStrategy, setEvaluationStrategy] = useState(null);
  const [splitsReady, setSplitsReadyState] = useState(false);

  const setSplitsReady = useCallback((value) => {
    spies.setSplitsReady(value);
    setSplitsReadyState(value);
  }, []);
  const setSplitter = useCallback((value) => {
    spies.setSplitter(value);
    setSplitterState(value);
  }, []);
  const setSplitPartitions = useCallback((value) => {
    spies.setSplitPartitions(value);
    setSplitPartitionsState(value);
  }, []);

  harness = {
    splitterParams,
    splitter,
    splitPartitions,
    strategyKind,
    groupColumn,
    rowsPartitionsIndex,
    splitType,
    evaluationStrategy,
    splitsReady,
  };

  return (
    <SplitDatasetRows
      datasetId={DATASET_ID}
      datasetInfo={datasetInfo}
      rowsPartitionsIndex={rowsPartitionsIndex}
      setRowsPartitionsIndex={setRowsPartitionsIndex}
      setSplitsReady={setSplitsReady}
      setSplitPartitions={setSplitPartitions}
      splitType={splitType}
      setSplitType={setSplitType}
      SPLIT_TYPES={SPLIT_TYPES}
      splitterParams={splitterParams}
      setSplitterParams={setSplitterParams}
      paramsError={paramsError}
      setParamsError={setParamsError}
      evaluationStrategy={evaluationStrategy}
      setEvaluationStrategy={setEvaluationStrategy}
      splitter={splitter}
      setSplitter={setSplitter}
      strategyKind={strategyKind}
      setStrategyKind={setStrategyKind}
      groupColumn={groupColumn}
      setGroupColumn={setGroupColumn}
      inputColumnNames={inputColumnNames}
      taskName={taskName}
    />
  );
}

const renderStep = ({
  datasetInfo = NO_PREDEFINED,
  inputColumnNames = ["a", "b", "group"],
  taskName = "TabularClassificationTask",
} = {}) =>
  renderWithProviders(
    <Harness
      datasetInfo={datasetInfo}
      taskName={taskName}
      inputColumnNames={inputColumnNames}
    />,
  );

const lastReady = () => {
  const { calls } = spies.setSplitsReady.mock;
  return calls.length ? calls[calls.length - 1][0] : undefined;
};

const lastPreviewRequest = () => {
  const { calls } = previewSplit.mock.calls.length ? previewSplit.mock : {};
  return calls ? calls[calls.length - 1][0] : undefined;
};

const ERROR_KEYS = [
  "trainSplitMustBeGreaterThanZero",
  "splitsMustSumToOne",
  "trainSplitMustHaveAtLeastOneRow",
  "foldsMustBeLessThanDatasetSize",
];
const errorText = (key, values = {}) =>
  i18n.t(`experiments:error.${key}`, values);

// Every split error message that is on screen, as translation keys.
const visibleErrorKeys = (datasetSize) =>
  ERROR_KEYS.filter((key) =>
    screen.queryByText(errorText(key, { datasetSize })),
  );

// Whether a message is shown under the splitter's form rather than in a card.
const isUnderForm = (element) =>
  element.closest(".MuiFormHelperText-root") !== null;

const toggle = (label) => screen.getByRole("button", { name: label });

const waitForSplitter = (name) => screen.findByTestId(`form-schema-${name}`);

const switchToCv = async () => {
  fireEvent.click(toggle("Cross-Validation"));
  await waitForSplitter(KFOLD.name);
};

const chooseSplitter = async (displayName) => {
  fireEvent.mouseDown(screen.getAllByRole("combobox")[0]);
  const listbox = await screen.findByRole("listbox");
  fireEvent.click(within(listbox).getByRole("option", { name: displayName }));
};

beforeEach(() => {
  mockFormParams = undefined;
  mockSchemasByName = {};
  spies.setSplitsReady = jest.fn();
  spies.setSplitter = jest.fn();
  spies.setSplitPartitions = jest.fn();
  getComponents.mockReset();
  mockComponents({});
  previewSplit.mockReset();
  previewSplit.mockResolvedValue(previewAnswer());
});

describe("SplitDatasetRows: evaluation strategy", () => {
  it("asks the backend for the splitters and the strategies of the task", async () => {
    renderStep();
    await waitForSplitter(HOLDOUT.name);

    expect(getComponents).toHaveBeenCalledWith({
      selectTypes: ["Splitter"],
      relatedComponent: "TabularClassificationTask",
    });
    expect(getComponents).toHaveBeenCalledWith({
      selectTypes: ["EvaluationStrategy"],
      relatedComponent: "TabularClassificationTask",
    });
  });

  it("selects the holdout strategy by default and labels the toggles with the strategies' display names", async () => {
    renderStep();
    await waitForSplitter(HOLDOUT.name);

    expect(harness.evaluationStrategy).toBe("HoldoutEvaluationStrategy");
    expect(harness.strategyKind).toBe("holdout");
    expect(toggle("Holdout")).toHaveAttribute("aria-pressed", "true");
    expect(toggle("Cross-Validation")).toHaveAttribute("aria-pressed", "false");
  });

  it("labels a toggle with the strategy name when the strategy has no display name", async () => {
    mockComponents({
      strategies: [
        HOLDOUT_STRATEGY,
        { ...CV_STRATEGY, display_name: undefined },
      ],
    });
    renderStep();
    await waitForSplitter(HOLDOUT.name);

    expect(toggle("CrossValidationEvaluationStrategy")).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("selects the first holdout kind strategy even when a cv strategy is listed first", async () => {
    mockComponents({ strategies: [CV_STRATEGY, HOLDOUT_STRATEGY] });
    renderStep();
    await waitForSplitter(HOLDOUT.name);

    expect(harness.evaluationStrategy).toBe("HoldoutEvaluationStrategy");
    expect(harness.strategyKind).toBe("holdout");
    expect(toggle("Holdout")).toHaveAttribute("aria-pressed", "true");
    // The toggles keep the order the backend listed the strategies in.
    const strategyToggles = toggle("Holdout").parentElement.children;
    expect(Array.from(strategyToggles).map((b) => b.textContent)).toEqual([
      "Cross-Validation",
      "Holdout",
    ]);
  });

  it("falls back to the first strategy when none is of holdout kind", async () => {
    mockComponents({ strategies: [CV_STRATEGY] });
    renderStep();
    await waitForSplitter(KFOLD.name);

    expect(harness.evaluationStrategy).toBe(
      "CrossValidationEvaluationStrategy",
    );
    expect(harness.strategyKind).toBe("cv");
  });

  it("shows no strategy toggle when the task offers only one strategy", async () => {
    mockComponents({ strategies: [HOLDOUT_STRATEGY] });
    renderStep();
    await waitForSplitter(HOLDOUT.name);

    expect(
      screen.queryByText(i18n.t("experiments:label.selectEvaluationStrategy")),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Cross-Validation" }),
    ).not.toBeInTheDocument();
  });

  it("switches to cross-validation when its toggle is clicked", async () => {
    renderStep();
    await waitForSplitter(HOLDOUT.name);
    await switchToCv();

    expect(harness.evaluationStrategy).toBe(
      "CrossValidationEvaluationStrategy",
    );
    expect(harness.strategyKind).toBe("cv");
    expect(toggle("Cross-Validation")).toHaveAttribute("aria-pressed", "true");
    expect(
      screen.queryByText(i18n.t("experiments:label.splitType")),
    ).not.toBeInTheDocument();
  });
});

describe("SplitDatasetRows: holdout", () => {
  it("offers predefined, random and manual, with predefined disabled and random selected when the dataset has no predefined splits", async () => {
    renderStep({ datasetInfo: NO_PREDEFINED });
    await waitForSplitter(HOLDOUT.name);

    expect(toggle("Predefined")).toBeDisabled();
    expect(toggle("Random")).toHaveAttribute("aria-pressed", "true");
    expect(toggle("Manual")).toHaveAttribute("aria-pressed", "false");
    expect(harness.splitType).toBe("random");
    expect(i18n.t("experiments:label.predefined")).toBe("Predefined");
    expect(i18n.t("experiments:label.random")).toBe("Random");
    expect(i18n.t("experiments:label.manual")).toBe("Manual");
  });

  it("selects predefined when the dataset carries train, validation or test sizes", async () => {
    renderStep({ datasetInfo: PREDEFINED });
    await waitForSplitter(HOLDOUT.name);

    expect(toggle("Predefined")).toBeEnabled();
    expect(toggle("Predefined")).toHaveAttribute("aria-pressed", "true");
    expect(harness.splitType).toBe("predefined");
    // The predefined proportions are shown, rounded to two decimals.
    expect(screen.getByDisplayValue("0.70")).toBeDisabled();
    expect(screen.getByDisplayValue("0.00")).toBeDisabled();
    expect(screen.getByDisplayValue("0.30")).toBeDisabled();
    await waitFor(() => expect(lastReady()).toBe(true));
  });

  it("starts on the strategy's declared default splitter (HoldoutSplitter) even when another holdout splitter is listed first, and never offers fold splitters for holdout", async () => {
    renderStep();
    await waitForSplitter(HOLDOUT.name);

    expect(spies.setSplitter).toHaveBeenLastCalledWith(HOLDOUT);
    expect(harness.splitter).toBe(HOLDOUT);
    expect(
      screen.getByTestId("form-schema-HoldoutSplitter"),
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId("form-schema-TemporalHoldoutSplitter"),
    ).not.toBeInTheDocument();
    // Holdout offers no splitter select at all.
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    await waitFor(() =>
      expect(lastPreviewRequest()).toMatchObject({
        datasetId: DATASET_ID,
        splitterName: "HoldoutSplitter",
        splitType: "random",
        indexes: null,
      }),
    );
  });

  it("starts on the first holdout splitter when the declared default is not offered", async () => {
    mockComponents({ splitters: [TEMPORAL_HOLDOUT, KFOLD] });
    renderStep();
    await waitForSplitter(TEMPORAL_HOLDOUT.name);

    expect(spies.setSplitter).toHaveBeenLastCalledWith(TEMPORAL_HOLDOUT);
  });

  it("starts on the first holdout splitter when the strategy declares no default", async () => {
    mockComponents({
      strategies: [
        {
          ...HOLDOUT_STRATEGY,
          metadata: { ...HOLDOUT_STRATEGY.metadata, default_splitter: null },
        },
        CV_STRATEGY,
      ],
    });
    renderStep();
    await waitForSplitter(TEMPORAL_HOLDOUT.name);

    expect(spies.setSplitter).toHaveBeenLastCalledWith(TEMPORAL_HOLDOUT);
  });

  it("hides only group_column from the generated form on a random split, and the proportions too on an index split", async () => {
    renderStep();
    const form = await waitForSplitter(HOLDOUT.name);
    expect(JSON.parse(form.dataset.excluded)).toEqual(["group_column"]);

    fireEvent.click(toggle("Manual"));
    await waitFor(() =>
      expect(
        JSON.parse(
          screen.getByTestId("form-schema-HoldoutSplitter").dataset.excluded,
        ),
      ).toEqual(["group_column", "train", "test", "validation"]),
    );
  });

  it("seeds the splitter parameters with the schema placeholders before the form is edited", async () => {
    mockSchemasByName = {
      HoldoutSplitter: {
        schema: {
          properties: {
            train: { type: "number", placeholder: 0.6 },
            validation: { type: "number", placeholder: 0.2 },
            test: { type: "number", placeholder: 0.2 },
            shuffle: { type: "boolean", placeholder: true },
            stratify: { type: "boolean" },
          },
        },
      },
    };
    renderStep();
    await waitForSplitter(HOLDOUT.name);

    await waitFor(() =>
      expect(harness.splitterParams).toEqual({
        train: 0.6,
        validation: 0.2,
        test: 0.2,
        shuffle: true,
      }),
    );
    expect(getComponents).toHaveBeenCalledWith({ model: "HoldoutSplitter" });
    await waitFor(() => expect(lastReady()).toBe(true));
    expect(lastPreviewRequest().params).toEqual({
      train: 0.6,
      validation: 0.2,
      test: 0.2,
      shuffle: true,
    });
  });

  it("asks for the preview with the splitter's defaults (none here) on a random split before the form is edited, and is not ready while the preview is pending", async () => {
    previewSplit.mockImplementation(() => new Promise(() => {}));
    renderStep();
    await waitForSplitter(HOLDOUT.name);
    await waitFor(() => expect(harness.splitType).toBe("random"));
    await waitFor(() =>
      expect(lastPreviewRequest()).toEqual({
        datasetId: DATASET_ID,
        splitterName: "HoldoutSplitter",
        params: {},
        splitType: "random",
        indexes: null,
      }),
    );

    // The splitter's own defaults, even when it has none: never the previous
    // splitter's parameters.
    expect(harness.splitterParams).toEqual({});
    expect(lastReady()).toBe(false);
    expect(visibleErrorKeys(150)).toEqual([]);
  });

  it("is not ready while the preview answers errors, and shows them under the form", async () => {
    previewSplit.mockResolvedValue(
      previewAnswer({ errors: [{ key: "splitsMustSumToOne", values: {} }] }),
    );
    mockFormParams = { train: 0.8, validation: 0.2, test: 0.2 };
    renderStep();
    await waitForSplitter(HOLDOUT.name);

    const message = await screen.findByText(errorText("splitsMustSumToOne"));
    expect(isUnderForm(message)).toBe(true);
    expect(lastReady()).toBe(false);
  });

  it("is not ready when the preview refuses the parameters (422), and shows the backend's reason under the form", async () => {
    previewSplit.mockRejectedValue({
      message: "Request failed with status code 422",
      response: {
        status: 422,
        data: { detail: "HoldoutSplitter cannot read these parameters" },
      },
    });
    mockFormParams = { train: 0.6, validation: 0.2, test: 0.2 };
    renderStep();
    await waitForSplitter(HOLDOUT.name);

    const message = await screen.findByText(
      "HoldoutSplitter cannot read these parameters",
    );
    expect(isUnderForm(message)).toBe(true);
    expect(
      JSON.parse(screen.getByTestId("split-preview").dataset.failure),
    ).toEqual({
      reason: "HoldoutSplitter cannot read these parameters",
      invalid: true,
    });
    await waitFor(() =>
      expect(spies.setSplitPartitions).toHaveBeenLastCalledWith(null),
    );
    expect(lastReady()).toBe(false);
  });

  it.each([
    [
      "a 500",
      {
        message: "Request failed with status code 500",
        response: { status: 500, data: { detail: "Internal database error" } },
      },
      "Internal database error",
    ],
    ["a network error", { message: "Network Error" }, "Network Error"],
  ])(
    "goes on when the preview fails with %s, on the partitions the strategy scores, and asks again on retry",
    async (_name, failure, reason) => {
      previewSplit.mockRejectedValueOnce(failure);
      mockFormParams = { train: 0.6, validation: 0.2, test: 0.2 };
      renderStep();
      await waitForSplitter(HOLDOUT.name);

      await waitFor(() => expect(lastReady()).toBe(true));
      expect(
        JSON.parse(screen.getByTestId("split-preview").dataset.failure),
      ).toEqual({ reason, invalid: false });
      expect(screen.queryByText(reason)).not.toBeInTheDocument();
      expect(spies.setSplitPartitions).toHaveBeenLastCalledWith(
        HOLDOUT_STRATEGY.metadata.scored_splits,
      );

      previewSplit.mockResolvedValueOnce(
        previewAnswer({ partitions: ["train", "test"] }),
      );
      fireEvent.click(screen.getByRole("button", { name: "retry-preview" }));

      await waitFor(() => expect(previewSplit).toHaveBeenCalledTimes(2));
      await waitFor(() =>
        expect(spies.setSplitPartitions).toHaveBeenLastCalledWith([
          "train",
          "test",
        ]),
      );
      expect(
        JSON.parse(screen.getByTestId("split-preview").dataset.failure),
      ).toBeNull();
    },
  );

  it("goes on when the splitter has no preview, on the partitions the strategy scores", async () => {
    previewSplit.mockResolvedValue(null);
    mockFormParams = { train: 0.6, validation: 0.2, test: 0.2 };
    renderStep();
    await waitForSplitter(HOLDOUT.name);
    await waitFor(() => expect(previewSplit).toHaveBeenCalled());

    await waitFor(() => expect(lastReady()).toBe(true));
    expect(spies.setSplitPartitions).toHaveBeenLastCalledWith(
      HOLDOUT_STRATEGY.metadata.scored_splits,
    );
    expect(
      JSON.parse(screen.getByTestId("split-preview").dataset.failure),
    ).toBeNull();
  });

  it("shows the preview's empty train error in the manual card and is not ready right after clicking Manual", async () => {
    previewSplit.mockImplementation(async ({ splitType, indexes }) =>
      splitType === "manual" && !indexes?.train?.length
        ? previewAnswer({
            errors: [{ key: "trainSplitMustHaveAtLeastOneRow", values: {} }],
            partitions: [],
          })
        : previewAnswer(),
    );
    mockFormParams = { train: 0.6, validation: 0.2, test: 0.2 };
    renderStep();
    await waitForSplitter(HOLDOUT.name);
    await waitFor(() => expect(lastReady()).toBe(true));

    fireEvent.click(toggle("Manual"));

    const message = await screen.findByText(
      errorText("trainSplitMustHaveAtLeastOneRow"),
    );
    expect(isUnderForm(message)).toBe(false);
    expect(harness.splitType).toBe("manual");
    expect(harness.rowsPartitionsIndex).toEqual({
      train: [],
      test: [],
      validation: [],
    });
    expect(lastPreviewRequest()).toMatchObject({
      splitType: "manual",
      indexes: { train: [], test: [], validation: [] },
    });
    await waitFor(() => expect(lastReady()).toBe(false));
  });

  it("reports the range parse error of a manual field as its message", async () => {
    renderStep({ datasetInfo: { ...NO_PREDEFINED, total_rows: 10 } });
    await waitForSplitter(HOLDOUT.name);
    fireEvent.click(toggle("Manual"));

    fireEvent.change(document.getElementById("train"), {
      target: { value: "0-50" },
    });

    expect(
      await screen.findByText(
        "The indexes should be minor than the total of columns or rows",
      ),
    ).toBeInTheDocument();
    expect(lastReady()).toBe(false);
  });

  it("shows the typed range parse error over the preview's error in the manual card", async () => {
    previewSplit.mockResolvedValue(
      previewAnswer({
        errors: [{ key: "trainSplitMustHaveAtLeastOneRow", values: {} }],
      }),
    );
    renderStep({ datasetInfo: { ...NO_PREDEFINED, total_rows: 10 } });
    await waitForSplitter(HOLDOUT.name);
    fireEvent.click(toggle("Manual"));
    await screen.findByText(errorText("trainSplitMustHaveAtLeastOneRow"));

    fireEvent.change(document.getElementById("train"), {
      target: { value: "0-50" },
    });

    expect(
      await screen.findByText(
        "The indexes should be minor than the total of columns or rows",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(errorText("trainSplitMustHaveAtLeastOneRow")),
    ).not.toBeInTheDocument();
    expect(lastReady()).toBe(false);
  });
});

describe("SplitDatasetRows: cross-validation", () => {
  it("offers only the fold splitters, in the order given, and starts on the first", async () => {
    renderStep();
    await waitForSplitter(HOLDOUT.name);
    await switchToCv();

    expect(spies.setSplitter).toHaveBeenCalledWith(KFOLD);
    expect(harness.splitter).toBe(KFOLD);
    expect(
      screen.getByText(i18n.t("experiments:label.cvType")),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(lastPreviewRequest()).toMatchObject({
        datasetId: DATASET_ID,
        splitterName: "KFoldSplitter",
        splitType: null,
        indexes: null,
      }),
    );

    fireEvent.mouseDown(screen.getAllByRole("combobox")[0]);
    const listbox = await screen.findByRole("listbox");
    expect(
      within(listbox)
        .getAllByRole("option")
        .map((option) => option.textContent),
    ).toEqual(["K-Fold", "Stratified", "Group K-Fold"]);
  });

  it("shows the group column card only for the splitter whose schema has group_column", async () => {
    renderStep();
    await waitForSplitter(HOLDOUT.name);
    await switchToCv();

    const groupLabel = i18n.t("experiments:label.groupColumn");
    expect(screen.queryByText(groupLabel)).not.toBeInTheDocument();
    await waitFor(() => expect(lastReady()).toBe(true));

    await chooseSplitter("Stratified");
    await waitForSplitter(STRATIFIED_KFOLD.name);
    expect(screen.queryByText(groupLabel)).not.toBeInTheDocument();

    await chooseSplitter("Group K-Fold");
    await waitForSplitter(GROUP_KFOLD.name);
    expect(screen.getByText(groupLabel)).toBeInTheDocument();
  });

  it("is not ready while the grouping splitter has no group column, and ready once one is chosen", async () => {
    renderStep();
    await waitForSplitter(HOLDOUT.name);
    await switchToCv();
    await chooseSplitter("Group K-Fold");
    await waitForSplitter(GROUP_KFOLD.name);

    await waitFor(() => expect(lastReady()).toBe(false));
    expect(harness.groupColumn).toBe("");

    const comboboxes = screen.getAllByRole("combobox");
    expect(comboboxes).toHaveLength(2);
    fireEvent.mouseDown(comboboxes[1]);
    const listbox = await screen.findByRole("listbox");
    expect(
      within(listbox)
        .getAllByRole("option")
        .map((option) => option.textContent),
    ).toEqual([i18n.t("experiments:label.selectAColumn"), "a", "b", "group"]);
    fireEvent.click(within(listbox).getByRole("option", { name: "group" }));

    await waitFor(() => expect(harness.groupColumn).toBe("group"));
    await waitFor(() => expect(lastReady()).toBe(true));
  });

  it("asks no preview with the previous splitter's parameters, and starts the new one on its own defaults", async () => {
    let seedKFold;
    const kfoldSchema = new Promise((resolve) => {
      seedKFold = resolve;
    });
    getComponents.mockImplementation(async (args) => {
      if (args.model === KFOLD.name) return kfoldSchema;
      if (args.model) return { schema: { properties: {} } };
      if (args.selectTypes?.[0] === "Splitter") return SPLITTERS;
      if (args.selectTypes?.[0] === "EvaluationStrategy") return STRATEGIES;
      return [];
    });
    mockFormParams = { train: 0.6, validation: 0.2, test: 0.2 };
    renderStep();
    await waitForSplitter(HOLDOUT.name);
    await waitFor(() => expect(lastReady()).toBe(true));

    // The new splitter's form reports nothing until it is edited.
    mockFormParams = undefined;
    await switchToCv();
    await new Promise((done) => setTimeout(done, 400));

    const kfoldRequests = () =>
      previewSplit.mock.calls
        .map(([request]) => request)
        .filter((request) => request.splitterName === KFOLD.name);
    expect(kfoldRequests()).toEqual([]);
    expect(lastReady()).toBe(false);

    seedKFold({
      schema: {
        properties: {
          n_splits: { type: "integer", placeholder: 5 },
          test_size: { type: "number", placeholder: 0 },
        },
      },
    });

    await waitFor(() => expect(kfoldRequests().length).toBeGreaterThan(0));
    kfoldRequests().forEach((request) =>
      expect(request.params).toEqual({ n_splits: 5, test_size: 0 }),
    );
    expect(harness.splitterParams).toEqual({ n_splits: 5, test_size: 0 });
    await waitFor(() => expect(lastReady()).toBe(true));
  });

  it.each([
    ["has no placeholders", async () => ({ schema: { properties: {} } })],
    [
      "cannot be fetched",
      async () => {
        throw new Error("Network Error");
      },
    ],
  ])(
    "drops the previous splitter's parameters when the new one's schema %s",
    async (_name, kfoldSchema) => {
      getComponents.mockImplementation(async (args) => {
        if (args.model === KFOLD.name) return kfoldSchema();
        if (args.model) return { schema: { properties: {} } };
        if (args.selectTypes?.[0] === "Splitter") return SPLITTERS;
        if (args.selectTypes?.[0] === "EvaluationStrategy") return STRATEGIES;
        return [];
      });
      jest.spyOn(console, "error").mockImplementation(() => {});
      mockFormParams = { train: 0.6, validation: 0.2, test: 0.2 };
      renderStep();
      await waitForSplitter(HOLDOUT.name);
      await waitFor(() => expect(lastReady()).toBe(true));

      mockFormParams = undefined;
      await switchToCv();

      await waitFor(() =>
        expect(lastPreviewRequest()).toMatchObject({
          splitterName: KFOLD.name,
          params: {},
        }),
      );
      previewSplit.mock.calls
        .map(([request]) => request)
        .filter((request) => request.splitterName === KFOLD.name)
        .forEach((request) => expect(request.params).toEqual({}));
      expect(harness.splitterParams).toEqual({});
      console.error.mockRestore();
    },
  );

  it("is not ready when no fold splitter is offered", async () => {
    mockComponents({ splitters: [HOLDOUT] });
    renderStep();
    await waitForSplitter(HOLDOUT.name);
    fireEvent.click(toggle("Cross-Validation"));

    await waitFor(() => expect(harness.strategyKind).toBe("cv"));
    await waitFor(() => expect(harness.splitter).toBeNull());
    await waitFor(() => expect(lastReady()).toBe(false));
    expect(screen.queryByTestId(/^form-schema-/)).not.toBeInTheDocument();
  });
});

describe("SplitDatasetRows: a strategy of any other kind", () => {
  const ORIGIN_SPLITTERS = [ORIGIN_TEMPORAL_HOLDOUT, ROLLING_ORIGIN, HOLDOUT];
  const ORIGIN_PARAMS = { horizon: 6, n_origins: 3, step: 1 };

  const renderBacktest = ({ splitters = ORIGIN_SPLITTERS } = {}) => {
    mockComponents({ splitters, strategies: [BACKTEST_STRATEGY] });
    mockFormParams = ORIGIN_PARAMS;
    return renderStep({ taskName: "SingleSeriesForecastingTask" });
  };

  it("starts on the splitter the strategy declares, and offers only its splitters in a splitter select", async () => {
    previewSplit.mockResolvedValue(
      previewAnswer({ partitions: ["validation", "test"] }),
    );
    renderBacktest();
    await waitForSplitter(ROLLING_ORIGIN.name);

    expect(harness.strategyKind).toBe("backtest");
    expect(spies.setSplitter).toHaveBeenLastCalledWith(ROLLING_ORIGIN);
    expect(
      screen.getByText(i18n.t("experiments:label.splitter")),
    ).toBeInTheDocument();
    // No holdout or cross-validation controls.
    expect(
      screen.queryByText(i18n.t("experiments:label.splitType")),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(i18n.t("experiments:label.cvType")),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId("split-preview")).toBeInTheDocument();

    expect(screen.getAllByRole("combobox")).toHaveLength(1);
    fireEvent.mouseDown(screen.getByRole("combobox"));
    const listbox = await screen.findByRole("listbox");
    expect(
      within(listbox)
        .getAllByRole("option")
        .map((option) => option.textContent),
    ).toEqual(["Temporal holdout", "Rolling origin"]);
  });

  it("asks for the preview with no split type and no indexes, and is ready when it answers no errors", async () => {
    previewSplit.mockResolvedValue(
      previewAnswer({ partitions: ["validation", "test"] }),
    );
    renderBacktest();
    await waitForSplitter(ROLLING_ORIGIN.name);

    await waitFor(() => expect(lastReady()).toBe(true));
    expect(lastPreviewRequest()).toEqual({
      datasetId: DATASET_ID,
      splitterName: "RollingOriginSplitter",
      params: ORIGIN_PARAMS,
      splitType: null,
      indexes: null,
    });
    await waitFor(() =>
      expect(spies.setSplitPartitions).toHaveBeenLastCalledWith([
        "validation",
        "test",
      ]),
    );
    expect(harness.splitPartitions).toEqual(["validation", "test"]);
  });

  it("shows the preview's seriesTooShort error under the form and is not ready", async () => {
    const values = { needed: 25, rows: 24, horizon: 6, origins: 3 };
    previewSplit.mockResolvedValue(
      previewAnswer({
        errors: [{ key: "seriesTooShort", values }],
        partitions: ["validation", "test"],
      }),
    );
    renderBacktest();
    await waitForSplitter(ROLLING_ORIGIN.name);

    const message = await screen.findByText(
      errorText("seriesTooShort", values),
    );
    expect(message).toHaveTextContent(
      "A horizon of 6 with 3 validation origin(s) needs at least 25 rows; the dataset has 24.",
    );
    expect(isUnderForm(message)).toBe(true);
    expect(lastReady()).toBe(false);
    await waitFor(() =>
      expect(spies.setSplitPartitions).toHaveBeenLastCalledWith([
        "validation",
        "test",
      ]),
    );
  });

  it("shows no splitter select when the strategy takes a single offered splitter", async () => {
    renderBacktest({ splitters: [ROLLING_ORIGIN, HOLDOUT] });
    await waitForSplitter(ROLLING_ORIGIN.name);

    expect(harness.splitter).toBe(ROLLING_ORIGIN);
    expect(
      screen.queryByText(i18n.t("experiments:label.splitter")),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    await waitFor(() => expect(lastReady()).toBe(true));
  });
});

// The same cases the backend runs (tests/back/splitters/test_split_preview.py):
// the preview answers each case's `expected`, and the step must send the case's
// request, show the errors it records, be ready exactly when it records none
// and pass on the partitions it reports.
describe("SplitDatasetRows: readiness and messages on the shared split cases", () => {
  const idsOf = (indexes) =>
    Object.entries(indexes).filter(([, rows]) => rows.length > 0);

  it.each(splitPreviewCases.map((c) => [c.name, c]))("%s", async (_name, c) => {
    const datasetSize = c.dataset.total_rows;
    const expectedErrors = c.expected.errors.map((error) => error.key);
    const expectedReady = expectedErrors.length === 0;
    const isCv = c.split_type === "cv";
    const isManual = c.split_type === "manual";
    previewSplit.mockResolvedValue(c.expected);

    if (c.split_type === "random") {
      mockFormParams = c.params;
      renderStep({ datasetInfo: c.dataset });
      await waitForSplitter(HOLDOUT.name);
      await waitFor(() => expect(harness.splitterParams).toEqual(c.params));
    } else if (isCv) {
      renderStep({ datasetInfo: c.dataset });
      await waitForSplitter(HOLDOUT.name);
      mockFormParams = c.params;
      await switchToCv();
      await waitFor(() => expect(harness.splitterParams).toEqual(c.params));
    } else if (isManual) {
      mockFormParams = c.params;
      renderStep({ datasetInfo: c.dataset });
      await waitForSplitter(HOLDOUT.name);
      fireEvent.click(toggle("Manual"));
      await waitFor(() => expect(harness.splitType).toBe("manual"));
      idsOf(c.indexes).forEach(([partition, rows]) => {
        fireEvent.change(document.getElementById(partition), {
          target: { value: parseIndexToRange(rows) },
        });
      });
      await waitFor(() =>
        expect(harness.rowsPartitionsIndex).toEqual(c.indexes),
      );
    } else if (c.split_type === "predefined") {
      mockFormParams = c.params;
      renderStep({ datasetInfo: c.dataset });
      await waitForSplitter(HOLDOUT.name);
      await waitFor(() => expect(harness.splitType).toBe("predefined"));
    } else {
      throw new Error(`No driver for split type ${c.split_type}`);
    }

    await waitFor(() =>
      expect(lastPreviewRequest()).toEqual({
        datasetId: DATASET_ID,
        splitterName: isCv ? KFOLD.name : HOLDOUT.name,
        params: c.params,
        splitType: isCv ? null : c.split_type,
        indexes: isManual ? c.indexes : null,
      }),
    );
    await waitFor(() => {
      expect(lastReady()).toBe(expectedReady);
      expect(visibleErrorKeys(datasetSize)).toEqual(expectedErrors);
    });
    c.expected.errors.forEach((error) => {
      const message = screen.getByText(errorText(error.key, error.values));
      expect(isUnderForm(message)).toBe(!isManual);
    });
    // Passive effects run after the commit that drew the messages.
    await waitFor(() =>
      expect(spies.setSplitPartitions).toHaveBeenLastCalledWith(
        c.expected.partitions,
      ),
    );
  });
});
