import React, { useCallback, useState } from "react";
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { renderWithProviders } from "../../../test-utils/renderWithProviders";
import i18n from "../../../utils/i18n";
import { getComponents } from "../../../api/component";
import { parseIndexToRange } from "../../../utils/parseRange";
import { SPLIT_TYPES } from "../../../utils/splitsPayload";
import splitPreviewCases from "./__fixtures__/splitPreviewCases.json";
import SplitDatasetRows from "./SplitDatasetRows";

/*
 * The splits step of the session wizard, pinned before its arithmetic and
 * validations move to the backend. The preview drawing itself is pinned by
 * src/utils/splitPreview.test.js on the same shared cases; here the cases pin
 * which messages the step shows and whether it lets the wizard go on.
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
  default: ({ geometry, splitType }) => (
    <div
      data-testid="split-preview"
      data-geometry={String(geometry)}
      data-split-type={String(splitType)}
    />
  ),
}));

const HOLDOUT_STRATEGY = {
  name: "HoldoutEvaluationStrategy",
  display_name: "Holdout",
  type: "EvaluationStrategy",
  metadata: { kind: "holdout", scored_splits: ["train", "validation", "test"] },
};
const CV_STRATEGY = {
  name: "CrossValidationEvaluationStrategy",
  display_name: "Cross validation",
  type: "EvaluationStrategy",
  metadata: { kind: "cv" },
};

const splitter = (name, displayName, metadata, properties = {}) => ({
  name,
  display_name: displayName,
  type: "Splitter",
  metadata,
  schema: { properties },
});

// Listed before HoldoutSplitter on purpose: the default holdout splitter is
// chosen by name, not by position.
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
  const [cvType, setCvTypeState] = useState(null);
  const [holdoutType, setHoldoutTypeState] = useState(null);
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
  const setHoldoutType = useCallback((value) => {
    spies.setHoldoutType(value);
    setHoldoutTypeState(value);
  }, []);
  const setCvType = useCallback((value) => {
    spies.setCvType(value);
    setCvTypeState(value);
  }, []);

  harness = {
    splitterParams,
    cvType,
    holdoutType,
    strategyKind,
    groupColumn,
    rowsPartitionsIndex,
    splitType,
    evaluationStrategy,
    splitsReady,
  };

  return (
    <SplitDatasetRows
      datasetInfo={datasetInfo}
      rowsPartitionsIndex={rowsPartitionsIndex}
      setRowsPartitionsIndex={setRowsPartitionsIndex}
      setSplitsReady={setSplitsReady}
      splitType={splitType}
      setSplitType={setSplitType}
      SPLIT_TYPES={SPLIT_TYPES}
      splitterParams={splitterParams}
      setSplitterParams={setSplitterParams}
      paramsError={paramsError}
      setParamsError={setParamsError}
      evaluationStrategy={evaluationStrategy}
      setEvaluationStrategy={setEvaluationStrategy}
      cvType={cvType}
      setCvType={setCvType}
      holdoutType={holdoutType}
      setHoldoutType={setHoldoutType}
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
} = {}) =>
  renderWithProviders(
    <Harness
      datasetInfo={datasetInfo}
      taskName="TabularClassificationTask"
      inputColumnNames={inputColumnNames}
    />,
  );

const lastReady = () => {
  const { calls } = spies.setSplitsReady.mock;
  return calls.length ? calls[calls.length - 1][0] : undefined;
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

const toggle = (label) => screen.getByRole("button", { name: label });

const holdoutLabel = () => i18n.t("experiments:label.holdout");
const cvLabel = () => i18n.t("experiments:label.crossValidation");

const waitForSplitter = (name) => screen.findByTestId(`form-schema-${name}`);

const switchToCv = async () => {
  fireEvent.click(toggle(cvLabel()));
  await waitForSplitter(KFOLD.name);
};

const chooseCvType = async (displayName) => {
  fireEvent.mouseDown(screen.getAllByRole("combobox")[0]);
  const listbox = await screen.findByRole("listbox");
  fireEvent.click(within(listbox).getByRole("option", { name: displayName }));
};

beforeEach(() => {
  mockFormParams = undefined;
  mockSchemasByName = {};
  spies.setSplitsReady = jest.fn();
  spies.setHoldoutType = jest.fn();
  spies.setCvType = jest.fn();
  getComponents.mockReset();
  mockComponents({});
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

  it("selects the holdout strategy by default and labels the toggles by kind, not by display name", async () => {
    renderStep();
    await waitForSplitter(HOLDOUT.name);

    expect(harness.evaluationStrategy).toBe("HoldoutEvaluationStrategy");
    expect(harness.strategyKind).toBe("holdout");
    expect(holdoutLabel()).toBe("Holdout");
    expect(cvLabel()).toBe("Cross-Validation");
    expect(toggle("Holdout")).toHaveAttribute("aria-pressed", "true");
    expect(toggle("Cross-Validation")).toHaveAttribute("aria-pressed", "false");
    expect(screen.queryByText("Cross validation")).not.toBeInTheDocument();
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

  it("starts on HoldoutSplitter even when another holdout splitter is listed first, and never offers fold splitters for holdout", async () => {
    renderStep();
    await waitForSplitter(HOLDOUT.name);

    expect(spies.setHoldoutType).toHaveBeenLastCalledWith(HOLDOUT);
    expect(harness.holdoutType).toBe(HOLDOUT);
    expect(
      screen.getByTestId("form-schema-HoldoutSplitter"),
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId("form-schema-TemporalHoldoutSplitter"),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId("split-preview")).toHaveAttribute(
      "data-geometry",
      "partitions",
    );
  });

  it("starts on the first holdout splitter when HoldoutSplitter is not offered", async () => {
    mockComponents({ splitters: [TEMPORAL_HOLDOUT, KFOLD] });
    renderStep();
    await waitForSplitter(TEMPORAL_HOLDOUT.name);

    expect(spies.setHoldoutType).toHaveBeenLastCalledWith(TEMPORAL_HOLDOUT);
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
  });

  it("is not ready on a random split before any parameter reaches it", async () => {
    renderStep();
    await waitForSplitter(HOLDOUT.name);
    await waitFor(() => expect(harness.splitType).toBe("random"));

    expect(harness.splitterParams).toBeNull();
    expect(lastReady()).toBe(false);
    expect(visibleErrorKeys(150)).toEqual([]);
  });

  it("shows the empty train error and is not ready right after clicking Manual", async () => {
    mockFormParams = { train: 0.6, validation: 0.2, test: 0.2 };
    renderStep();
    await waitForSplitter(HOLDOUT.name);
    await waitFor(() => expect(lastReady()).toBe(true));

    fireEvent.click(toggle("Manual"));

    expect(
      await screen.findByText(errorText("trainSplitMustHaveAtLeastOneRow")),
    ).toBeInTheDocument();
    expect(harness.splitType).toBe("manual");
    expect(harness.rowsPartitionsIndex).toEqual({
      train: [],
      test: [],
      validation: [],
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
});

describe("SplitDatasetRows: cross-validation", () => {
  it("offers only the fold splitters, in the order given, and starts on the first", async () => {
    renderStep();
    await waitForSplitter(HOLDOUT.name);
    await switchToCv();

    expect(spies.setCvType).toHaveBeenCalledWith(KFOLD);
    expect(harness.cvType).toBe(KFOLD);
    expect(
      screen.getByText(i18n.t("experiments:label.cvType")),
    ).toBeInTheDocument();
    expect(screen.getByTestId("split-preview")).toHaveAttribute(
      "data-geometry",
      "blocked_folds",
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

    await chooseCvType("Stratified");
    await waitForSplitter(STRATIFIED_KFOLD.name);
    expect(screen.queryByText(groupLabel)).not.toBeInTheDocument();

    await chooseCvType("Group K-Fold");
    await waitForSplitter(GROUP_KFOLD.name);
    expect(screen.getByText(groupLabel)).toBeInTheDocument();
  });

  it("is not ready while the grouping splitter has no group column, and ready once one is chosen", async () => {
    renderStep();
    await waitForSplitter(HOLDOUT.name);
    await switchToCv();
    await chooseCvType("Group K-Fold");
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

  it("is not ready when no fold splitter is offered", async () => {
    mockComponents({ splitters: [HOLDOUT] });
    renderStep();
    await waitForSplitter(HOLDOUT.name);
    fireEvent.click(toggle("Cross-Validation"));

    await waitFor(() => expect(harness.strategyKind).toBe("cv"));
    expect(harness.cvType).toBeNull();
    await waitFor(() => expect(lastReady()).toBe(false));
    expect(screen.queryByTestId(/^form-schema-/)).not.toBeInTheDocument();
  });
});

// The same cases the preview net and the backend run: the step must show the
// errors they record, and be ready exactly when they record none.
describe("SplitDatasetRows: readiness and messages on the shared split cases", () => {
  const idsOf = (indexes) =>
    Object.entries(indexes).filter(([, rows]) => rows.length > 0);

  it.each(splitPreviewCases.map((c) => [c.name, c]))("%s", async (_name, c) => {
    const datasetSize = c.dataset.total_rows;
    const expectedErrors = c.expected.errors.map((error) => error.key);
    const expectedReady = expectedErrors.length === 0;

    if (c.split_type === "random") {
      mockFormParams = c.params;
      renderStep({ datasetInfo: c.dataset });
      await waitForSplitter(HOLDOUT.name);
      await waitFor(() => expect(harness.splitterParams).toEqual(c.params));
    } else if (c.split_type === "cv") {
      renderStep({ datasetInfo: c.dataset });
      await waitForSplitter(HOLDOUT.name);
      mockFormParams = c.params;
      await switchToCv();
      await waitFor(() => expect(harness.splitterParams).toEqual(c.params));
    } else if (c.split_type === "manual") {
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
      renderStep({ datasetInfo: c.dataset });
      await waitForSplitter(HOLDOUT.name);
      await waitFor(() => expect(harness.splitType).toBe("predefined"));
    } else {
      throw new Error(`No driver for split type ${c.split_type}`);
    }

    await waitFor(() => expect(lastReady()).toBe(expectedReady));
    expect(visibleErrorKeys(datasetSize)).toEqual(expectedErrors);
    c.expected.errors.forEach((error) => {
      expect(
        screen.getByText(errorText(error.key, error.values)),
      ).toBeInTheDocument();
    });
  });
});
