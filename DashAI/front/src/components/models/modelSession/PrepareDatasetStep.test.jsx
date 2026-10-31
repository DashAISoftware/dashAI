import React, { useCallback, useState } from "react";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../../test-utils/renderWithProviders";
import i18n from "../../../utils/i18n";
import { getComponents } from "../../../api/component";
import { previewSplit } from "../../../api/splitter";
import PrepareDatasetStep from "./PrepareDatasetStep";

/*
 * The splits payload PrepareDatasetStep writes into newExp.splits, with the
 * real SplitDatasetRows in the right bar as the wizard renders it. The pure
 * pieces are pinned by src/utils/splitsPayload.test.js.
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

// A stand-in for POST /splitter/preview. What the splitter answers is pinned
// by the backend's tests on the shared cases; here it only has to say which
// partitions receive rows and whether the proportions sum to one.
const fakePreview = async ({ params, splitType, indexes }) => {
  const answer = { rows: [], notes: [], shares: {}, errors: [] };
  const partitions = ["train", "validation", "test"];
  if (splitType === "random") {
    const sum = params.train + params.validation + params.test;
    if (Math.abs(sum - 1) >= 0.0001) {
      answer.errors = [{ key: "splitsMustSumToOne", values: {} }];
    }
    answer.partitions = partitions.filter((name) => params[name]);
  } else if (splitType === "manual") {
    answer.partitions = partitions.filter((name) => indexes?.[name]?.length);
  } else if (splitType === "predefined") {
    answer.partitions = ["train", "test"];
  } else if (params.n_splits !== undefined) {
    answer.partitions = ["train", "validation"].concat(
      params.test_size ? ["test"] : [],
    );
  } else {
    answer.partitions = ["validation", "test"];
  }
  return answer;
};

let mockSetSessionRightContent;
jest.mock("../ModelsContext", () => ({
  useModels: () => ({ setSessionRightContent: mockSetSessionRightContent }),
}));

let mockFormParams;
jest.mock("../../shared/FormSchema", () => {
  const ReactInStub = require("react");
  function FormSchemaStub(props) {
    ReactInStub.useEffect(() => {
      if (mockFormParams !== undefined) props.onFormSubmit(mockFormParams);
    }, []);
    return <div data-testid={`form-schema-${props.model}`} />;
  }
  return { __esModule: true, default: FormSchemaStub };
});

jest.mock("./SplitPreview", () => ({
  __esModule: true,
  default: () => <div data-testid="split-preview" />,
}));

const STRATEGIES = [
  {
    name: "HoldoutEvaluationStrategy",
    display_name: "Holdout",
    metadata: {
      kind: "holdout",
      scored_splits: ["train", "validation", "test"],
      splitter_partitioning: "holdout",
      default_splitter: "HoldoutSplitter",
      result_views: [],
    },
  },
  {
    name: "CrossValidationEvaluationStrategy",
    display_name: "Cross-Validation",
    metadata: {
      kind: "cv",
      splitter_partitioning: "folds",
      default_splitter: null,
      result_views: ["fold_metrics"],
    },
  },
];
const SPLITTERS = [
  {
    name: "HoldoutSplitter",
    display_name: "Holdout",
    metadata: { partitioning: "holdout", geometry: "partitions" },
    schema: { properties: {} },
  },
  {
    name: "KFoldSplitter",
    display_name: "K-Fold",
    metadata: { partitioning: "folds", geometry: "blocked_folds" },
    schema: { properties: {} },
  },
];

const NO_PREDEFINED = {
  total_rows: 10,
  train_size: 0,
  val_size: 0,
  test_size: 0,
  column_names: ["a", "b"],
};

const spies = {};

function Host({ datasetInfo, taskName = "TabularClassificationTask" }) {
  const [rightContent, setRightContent] = useState(null);
  mockSetSessionRightContent = (content) => {
    spies.pushedRightContent?.();
    setRightContent(content);
  };
  const [evaluationStrategy, setEvaluationStrategy] = useState(null);
  const [newExp, setNewExpState] = useState({
    task_name: taskName,
    splits: {},
  });
  const setNewExp = useCallback((value) => {
    spies.setNewExp(value);
    setNewExpState(value);
  }, []);

  return (
    <>
      <PrepareDatasetStep
        newExp={newExp}
        setNewExp={setNewExp}
        setNextEnabled={spies.setNextEnabled}
        dataset={{ id: 1 }}
        evaluationStrategy={evaluationStrategy}
        setEvaluationStrategy={setEvaluationStrategy}
        datasetInfo={datasetInfo}
        infoLoading={false}
      />
      {rightContent}
    </>
  );
}

const renderStep = (datasetInfo = NO_PREDEFINED, taskName = undefined) =>
  renderWithProviders(<Host datasetInfo={datasetInfo} taskName={taskName} />);

const lastNewExp = () => {
  const { calls } = spies.setNewExp.mock;
  return calls.length ? calls[calls.length - 1][0] : undefined;
};
const lastNextEnabled = () => {
  const { calls } = spies.setNextEnabled.mock;
  return calls.length ? calls[calls.length - 1][0] : undefined;
};

const toggle = (label) => screen.getByRole("button", { name: label });

beforeEach(() => {
  mockFormParams = undefined;
  spies.setNewExp = jest.fn();
  spies.setNextEnabled = jest.fn();
  previewSplit.mockReset();
  previewSplit.mockImplementation(fakePreview);
  getComponents.mockReset();
  getComponents.mockImplementation(async (args) => {
    if (args.model) return { schema: { properties: {} } };
    if (args.selectTypes?.[0] === "Splitter") return SPLITTERS;
    if (args.selectTypes?.[0] === "EvaluationStrategy") return STRATEGIES;
    return [];
  });
});

describe("PrepareDatasetStep writes newExp.splits", () => {
  it("holdout random: the form values with splitter_name and splitType random", async () => {
    mockFormParams = {
      train: 0.6,
      validation: 0.2,
      test: 0.2,
      shuffle: true,
      random_state: 7,
    };
    renderStep();
    await screen.findByTestId("form-schema-HoldoutSplitter");

    await waitFor(() =>
      expect(lastNewExp()?.splits).toEqual({
        splitter_name: "HoldoutSplitter",
        splitType: "random",
        train: 0.6,
        validation: 0.2,
        test: 0.2,
        shuffle: true,
        random_state: 7,
      }),
    );
    expect(lastNewExp()).toMatchObject({
      task_name: "TabularClassificationTask",
      evaluation_strategy: "HoldoutEvaluationStrategy",
      applyPreprocessing: false,
      // As the splitter's preview answered: they pick the session's metrics.
      splitPartitions: ["train", "validation", "test"],
    });
    expect(lastNextEnabled()).toBe(true);
  });

  it("holdout random that does not sum to one: newExp is not updated and Next stays disabled", async () => {
    mockFormParams = { train: 0.8, validation: 0.2, test: 0.2 };
    renderStep();
    await screen.findByTestId("form-schema-HoldoutSplitter");
    await screen.findByText(i18n.t("experiments:error.splitsMustSumToOne"));

    expect(spies.setNewExp).not.toHaveBeenCalled();
    expect(lastNextEnabled()).toBe(false);
  });

  it("holdout manual: the typed indexes in splitted_indexes and no proportions", async () => {
    mockFormParams = { train: 0.6, validation: 0.2, test: 0.2, shuffle: true };
    renderStep();
    await screen.findByTestId("form-schema-HoldoutSplitter");

    fireEvent.click(toggle(i18n.t("experiments:label.manual")));
    await waitFor(() => expect(lastNextEnabled()).toBe(false));
    fireEvent.change(document.getElementById("train"), {
      target: { value: "0-5" },
    });
    fireEvent.change(document.getElementById("validation"), {
      target: { value: "6-7" },
    });
    fireEvent.change(document.getElementById("test"), {
      target: { value: "8,9" },
    });

    await waitFor(() =>
      expect(lastNewExp()?.splits).toEqual({
        splitter_name: "HoldoutSplitter",
        splitType: "manual",
        shuffle: true,
        splitted_indexes: {
          train_indexes: [0, 1, 2, 3, 4, 5],
          test_indexes: [8, 9],
          val_indexes: [6, 7],
        },
      }),
    );
    expect(lastNextEnabled()).toBe(true);
  });

  it("holdout predefined: the dataset's own indexes in splitted_indexes", async () => {
    mockFormParams = { train: 0.6, validation: 0.2, test: 0.2 };
    renderStep({
      ...NO_PREDEFINED,
      train_size: 7,
      test_size: 3,
      train_indices: [0, 1, 2, 3, 4, 5, 6],
      test_indices: [7, 8, 9],
      predefined_splits: { train: 0.7, validation: 0, test: 0.3 },
    });
    await screen.findByTestId("form-schema-HoldoutSplitter");

    await waitFor(() =>
      expect(lastNewExp()?.splits).toEqual({
        splitter_name: "HoldoutSplitter",
        splitType: "predefined",
        splitted_indexes: {
          train_indexes: [0, 1, 2, 3, 4, 5, 6],
          test_indexes: [7, 8, 9],
          val_indexes: [],
        },
      }),
    );
  });

  it("cv without test_size: splitType cv with the fold splitter's values", async () => {
    mockFormParams = { n_splits: 5, shuffle: false };
    renderStep();
    await screen.findByTestId("form-schema-HoldoutSplitter");

    fireEvent.click(toggle(i18n.t("experiments:label.crossValidation")));
    await screen.findByTestId("form-schema-KFoldSplitter");

    await waitFor(() =>
      expect(lastNewExp()?.splits).toEqual({
        splitter_name: "KFoldSplitter",
        splitType: "cv",
        n_splits: 5,
        shuffle: false,
      }),
    );
    expect(lastNewExp().evaluation_strategy).toBe(
      "CrossValidationEvaluationStrategy",
    );
    expect(lastNewExp().splitPartitions).toEqual(["train", "validation"]);
    expect(lastNextEnabled()).toBe(true);
  });

  it("cv with test_size: test_size kept at the top level", async () => {
    mockFormParams = { n_splits: 5, test_size: 0.2 };
    renderStep();
    await screen.findByTestId("form-schema-HoldoutSplitter");

    fireEvent.click(toggle(i18n.t("experiments:label.crossValidation")));
    await screen.findByTestId("form-schema-KFoldSplitter");

    await waitFor(() =>
      expect(lastNewExp()?.splits).toEqual({
        splitter_name: "KFoldSplitter",
        splitType: "cv",
        n_splits: 5,
        test_size: 0.2,
      }),
    );
  });

  it("a strategy without a form of its own: the splitter's parameters alone, with no split type", async () => {
    getComponents.mockImplementation(async (args) => {
      if (args.model) return { schema: { properties: {} } };
      if (args.selectTypes?.[0] === "Splitter") {
        return [
          {
            name: "RollingOriginSplitter",
            display_name: "Rolling origin",
            metadata: { partitioning: "origins" },
            schema: { properties: {} },
          },
        ];
      }
      if (args.selectTypes?.[0] === "EvaluationStrategy") {
        return [
          {
            name: "ForecastingCrossValidationEvaluationStrategy",
            display_name: "Cross-Validation",
            metadata: {
              kind: "backtest",
              splitter_partitioning: "origins",
              default_splitter: "RollingOriginSplitter",
              result_views: ["fold_metrics", "forecasts"],
            },
          },
        ];
      }
      return [];
    });
    mockFormParams = { horizon: 3, n_origins: 4 };
    renderStep();
    await screen.findByTestId("form-schema-RollingOriginSplitter");

    await waitFor(() =>
      expect(JSON.parse(JSON.stringify(lastNewExp()?.splits))).toEqual({
        splitter_name: "RollingOriginSplitter",
        horizon: 3,
        n_origins: 4,
      }),
    );
    expect(lastNewExp().splitPartitions).toEqual(["validation", "test"]);
    expect(lastNextEnabled()).toBe(true);
  });
});

describe("PrepareDatasetStep pushes the splits step into the right bar", () => {
  it("settles, although the wizard hands it a new dataset object on every render", async () => {
    // Host passes dataset={{ id: 1 }}, a new object each render, as the
    // wizard does. Depending on the object rather than its id re-pushed the
    // step, which re-rendered the host, without end.
    // A loop starves the timers the test waits on, so it is cut short here,
    // where it shows, instead of hanging the run.
    let pushes = 0;
    spies.pushedRightContent = () => {
      pushes += 1;
      if (pushes > 100) {
        throw new Error(`The splits step was pushed ${pushes} times`);
      }
    };
    renderStep();
    await screen.findByTestId("form-schema-HoldoutSplitter");
    await waitFor(() => expect(lastNextEnabled()).toBe(true));

    const settled = pushes;
    await new Promise((done) => setTimeout(done, 300));

    expect(pushes).toBe(settled);
    spies.pushedRightContent = undefined;
  });
});

describe("PrepareDatasetStep offers session preprocessing as the task says", () => {
  const withTaskMetadata = (metadata) => {
    const fallback = getComponents.getMockImplementation();
    getComponents.mockImplementation(async (args) => {
      if (args.model?.endsWith("Task")) return { name: args.model, metadata };
      return fallback(args);
    });
  };

  it("hides the switch for a task that takes no preprocessing", async () => {
    withTaskMetadata({ takes_preprocessing: false });
    mockFormParams = { train: 0.6, validation: 0.2, test: 0.2 };
    renderStep(NO_PREDEFINED, "NoPreprocessingTask");
    await screen.findByTestId("form-schema-HoldoutSplitter");
    await waitFor(() => expect(lastNextEnabled()).toBe(true));
    await waitFor(() =>
      expect(getComponents).toHaveBeenCalledWith({
        model: "NoPreprocessingTask",
      }),
    );

    expect(
      screen.queryByText(i18n.t("models:label.applyPreprocessing")),
    ).not.toBeInTheDocument();
  });

  it("shows it for a task that takes preprocessing", async () => {
    withTaskMetadata({ takes_preprocessing: true });
    mockFormParams = { train: 0.6, validation: 0.2, test: 0.2 };
    renderStep(NO_PREDEFINED, "PreprocessingTask");

    expect(
      await screen.findByText(i18n.t("models:label.applyPreprocessing")),
    ).toBeInTheDocument();
  });
});
