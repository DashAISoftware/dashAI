import React from "react";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import i18n from "../../utils/i18n";
import { getComponents } from "../../api/component";
import ModelsRightBar from "./ModelsRightBar";

/*
 * The right bar of a session. The statistical tests compare runs fold by
 * fold, so they are offered when the strategy declares a score per fold or
 * origin (`result_views`), the same declaration the session view reads.
 */

jest.mock("react-markdown", () => ({
  __esModule: true,
  default: ({ children }) => <span>{children}</span>,
}));
jest.mock("../../api/component", () => ({ getComponents: jest.fn() }));
jest.mock("notistack", () => {
  const snackbar = { enqueueSnackbar: jest.fn(), closeSnackbar: jest.fn() };
  return { useSnackbar: () => snackbar };
});
jest.mock("../tour/TourProvider", () => ({ useTourContext: () => null }));
jest.mock("./model/ComponentDownloadControl", () => ({
  startComponentDownload: jest.fn(),
  subscribeAnyDownloadState: () => () => {},
  useComponentDownloadState: () => ({ downloaded: true, downloading: false }),
}));
jest.mock("../credentials/credentialStatus", () => ({
  useCredentialStatuses: () => ({ statuses: {}, loaded: true }),
  getComponentCredentialState: () => ({}),
}));
jest.mock("./StatisticalTestsList", () => () => (
  <div data-testid="statistical-tests-list" />
));
jest.mock("./StatisticalTestsModal", () => () => null);
jest.mock("./AddModelDialog", () => () => null);

const mockCloseStatisticalTest = jest.fn();
let mockSession;
jest.mock("./ModelsContext", () => ({
  useModels: () => ({
    selectedSession: mockSession,
    runs: [],
    datasets: [],
    tasks: [],
    getModelsForTask: async () => [],
    closeStatisticalTest: mockCloseStatisticalTest,
    openStatisticalTest: jest.fn(),
    statisticalTestsModalOpen: false,
  }),
}));

const STRATEGIES = {
  CrossValidationEvaluationStrategy: {
    kind: "cv",
    result_views: ["fold_metrics"],
  },
  ForecastingCrossValidationEvaluationStrategy: {
    kind: "backtest",
    result_views: ["fold_metrics", "forecasts"],
  },
  ForecastingHoldoutEvaluationStrategy: {
    kind: "backtest",
    result_views: ["forecasts"],
  },
  HoldoutEvaluationStrategy: { kind: "holdout", result_views: [] },
};

const testsTab = () =>
  screen.queryByRole("tab", { name: i18n.t("models:label.statisticalTests") });

beforeEach(() => {
  getComponents.mockImplementation(async ({ model }) => ({
    name: model,
    metadata: STRATEGIES[model] ?? {},
  }));
});

describe("ModelsRightBar offers the statistical tests", () => {
  it.each([
    ["a cross-validation", "CrossValidationEvaluationStrategy"],
    [
      "a cross-validation backtest",
      "ForecastingCrossValidationEvaluationStrategy",
    ],
  ])(
    "for %s, whose strategy scores each fold or origin",
    async (_name, strategy) => {
      mockSession = { id: 1, task_name: "T", evaluation_strategy: strategy };
      renderWithProviders(<ModelsRightBar onToggle={jest.fn()} />);

      expect(
        await screen.findByRole("tab", {
          name: i18n.t("models:label.statisticalTests"),
        }),
      ).toBeInTheDocument();
    },
  );

  it.each([
    ["a holdout", "HoldoutEvaluationStrategy"],
    ["a single-origin backtest", "ForecastingHoldoutEvaluationStrategy"],
  ])("not for %s, which has no score per fold", async (_name, strategy) => {
    mockSession = { id: 1, task_name: "T", evaluation_strategy: strategy };
    renderWithProviders(<ModelsRightBar onToggle={jest.fn()} />);

    await waitFor(() =>
      expect(getComponents).toHaveBeenCalledWith({ model: strategy }),
    );
    await new Promise((done) => setTimeout(done, 50));
    expect(testsTab()).not.toBeInTheDocument();
  });
});
