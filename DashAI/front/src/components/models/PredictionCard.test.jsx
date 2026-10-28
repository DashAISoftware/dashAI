import React from "react";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import PredictionCard from "./PredictionCard";
import { getDatasetTypesByFilePath } from "../../api/datasets";

jest.mock("notistack", () => {
  const snackbar = { enqueueSnackbar: jest.fn(), closeSnackbar: jest.fn() };
  return { useSnackbar: () => snackbar };
});
jest.mock("../../api/predict", () => ({ deletePrediction: jest.fn() }));
jest.mock("../../api/datasets", () => ({
  getDatasetFile: jest.fn(),
  getDatasetFileFiltered: jest.fn(),
  exportDatasetCsvByPath: jest.fn(),
  getDatasetTypesByFilePath: jest.fn(),
}));
jest.mock("../notebooks/dataset/DatasetTable", () => () => (
  <div data-testid="results" />
));

const finished = (extra) => ({
  id: 7,
  status: 3,
  results_path: "/tmp/prediction",
  ...extra,
});

describe("PredictionCard", () => {
  beforeEach(() => {
    getDatasetTypesByFilePath.mockResolvedValue({});
  });

  it("warns about the categories the model never saw in training", () => {
    renderWithProviders(
      <PredictionCard
        prediction={finished({
          unseen_categories: [
            {
              source: "OneHotEncoder (step 1)",
              column: "color",
              values: ["purple", "teal"],
              count: 2,
            },
          ],
        })}
      />,
    );

    expect(
      screen.getByText("Categories the model never saw in training"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("color (OneHotEncoder (step 1)): purple, teal"),
    ).toBeInTheDocument();
  });

  it("says how many more values there were than it lists", () => {
    renderWithProviders(
      <PredictionCard
        prediction={finished({
          unseen_categories: [
            {
              source: "RandomForestClassifier (model)",
              column: "city",
              values: ["a", "b"],
              count: 25,
            },
          ],
        })}
      />,
    );

    expect(
      screen.getByText(
        "city (RandomForestClassifier (model)): a, b and 23 more",
      ),
    ).toBeInTheDocument();
  });

  it.each([[[]], [null], [undefined]])(
    "shows no warning when nothing was unseen (%p)",
    (unseen) => {
      renderWithProviders(
        <PredictionCard prediction={finished({ unseen_categories: unseen })} />,
      );

      expect(
        screen.queryByText("Categories the model never saw in training"),
      ).not.toBeInTheDocument();
    },
  );
});
