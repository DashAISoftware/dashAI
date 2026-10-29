import React, { useCallback, useState } from "react";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../../test-utils/renderWithProviders";
import i18n from "../../../utils/i18n";
import { getComponents } from "../../../api/component";
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
    },
  },
  {
    name: "CrossValidationEvaluationStrategy",
    display_name: "Cross validation",
    metadata: { kind: "cv" },
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

function Host({ datasetInfo }) {
  const [rightContent, setRightContent] = useState(null);
  mockSetSessionRightContent = setRightContent;
  const [evaluationStrategy, setEvaluationStrategy] = useState(null);
  const [newExp, setNewExpState] = useState({
    task_name: "TabularClassificationTask",
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

const renderStep = (datasetInfo = NO_PREDEFINED) =>
  renderWithProviders(<Host datasetInfo={datasetInfo} />);

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
});
