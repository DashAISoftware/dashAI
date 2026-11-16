import { getComponents } from "../api/component";
import { getInstalledPlugins } from "../api/plugins";
import {
  checkUnavailable,
  confirmAvailable,
  generativeSessionComponents,
  runNeeds,
  sessionComponents,
  unavailableComponents,
  unavailableText,
} from "./componentAvailability";

jest.mock("../api/component", () => ({ getComponents: jest.fn() }));
jest.mock("../api/plugins", () => ({ getInstalledPlugins: jest.fn() }));

const todo = (overrides = {}) => ({
  id: "plugin-todo",
  name: "Plugin Todo",
  components: ["TodoDummyClassifier", "TodoAccuracy"],
  enabled: true,
  problem: null,
  ...overrides,
});

const session = {
  task_name: "TabularClassificationTask",
  train_metrics: ["Accuracy", "TodoAccuracy"],
  validation_metrics: null,
  test_metrics: ["Accuracy"],
  preprocessing: { steps: [{ converter: "TodoStandardScaler", params: {} }] },
};
const run = {
  model_name: "DummyClassifier",
  optimizer_name: "OptunaOptimizer",
  goal_metric: "TodoF1",
};
const registered = new Set([
  "TabularClassificationTask",
  "Accuracy",
  "DummyClassifier",
]);

// t() as i18next resolves it here, the key and its params.
const t = (key, options) => JSON.stringify({ key, ...options });

// Each row of NEEDS, as its job uses the registry.
describe("what each action on a run needs", () => {
  const needs = (action) => new Set(runNeeds(action, run, session));

  it("training needs everything: model, optimizer, goal metric, task, metrics, preprocessing", () => {
    expect(needs("train")).toEqual(
      new Set([
        "DummyClassifier",
        "OptunaOptimizer",
        "TodoF1",
        "TabularClassificationTask",
        "Accuracy",
        "TodoAccuracy",
        "TodoStandardScaler",
      ]),
    );
  });

  it("predicting and explaining need the model, the task and the preprocessing", () => {
    const used = new Set([
      "DummyClassifier",
      "TabularClassificationTask",
      "TodoStandardScaler",
    ]);
    expect(needs("predict")).toEqual(used);
    expect(needs("explain")).toEqual(used);
  });

  it("a report needs only the model and the task", () => {
    expect(needs("report")).toEqual(
      new Set(["DummyClassifier", "TabularClassificationTask"]),
    );
  });

  it("a session needs what any of its runs needs besides model and optimizer", () => {
    expect(new Set(sessionComponents(session))).toEqual(
      new Set([
        "TabularClassificationTask",
        "Accuracy",
        "TodoAccuracy",
        "TodoStandardScaler",
      ]),
    );
    expect(sessionComponents(null)).toEqual([]);
  });

  it("a run without HPO or preprocessing needs nothing it doesn't name", () => {
    const plain = { model_name: "DummyClassifier", optimizer_name: "" };
    const bare = { task_name: "TabularClassificationTask" };
    expect(runNeeds("train", plain, bare)).toEqual([
      "DummyClassifier",
      "TabularClassificationTask",
    ]);
  });
});

describe("what a generative session needs", () => {
  it("includes the components nested in a RAG session's parameters", () => {
    const rag = {
      task_name: "RAGTask",
      model_name: "RAGPipeline",
      parameters: {
        retriever_model: {
          component: "BM25Retriever",
          params: { BM25Vectorizer: { component: "BM25VectorizerModel" } },
        },
        generation_model: { component: "TodoEchoModel", params: {} },
        documents: [1],
      },
    };
    expect(generativeSessionComponents(rag)).toEqual([
      "RAGTask",
      "RAGPipeline",
      "BM25Retriever",
      "BM25VectorizerModel",
      "TodoEchoModel",
    ]);
    expect(generativeSessionComponents(null)).toEqual([]);
  });
});

describe("unavailableComponents", () => {
  it("blocks training a native run whose session uses a disabled plugin's metric", () => {
    const native = { model_name: "DummyClassifier", optimizer_name: null };
    const { preprocessing, ...noPreprocessing } = session;
    const missing = unavailableComponents(
      runNeeds("train", native, noPreprocessing),
      registered,
      [todo({ enabled: false })],
    );
    expect(missing).toEqual([
      {
        name: "TodoAccuracy",
        plugin: todo({ enabled: false }),
        reason: "disabled",
      },
    ]);
  });

  it("tells disabled, problem and uninstalled apart", () => {
    const reasons = (plugins) =>
      unavailableComponents(["TodoAccuracy"], registered, plugins).map(
        (item) => item.reason,
      );
    expect(reasons([todo({ enabled: false })])).toEqual(["disabled"]);
    expect(reasons([todo({ problem: { code: "load_failed" } })])).toEqual([
      "problem",
    ]);
    expect(reasons([])).toEqual(["uninstalled"]);
  });

  it("misses nothing before the registry was read, or when it is there", () => {
    expect(unavailableComponents(["TodoAccuracy"], null, [])).toEqual([]);
    expect(
      unavailableComponents(["Accuracy", null, undefined], registered, []),
    ).toEqual([]);
  });

  it("finds a missing component's plugin by its id", () => {
    const missing = unavailableComponents(
      ["plugin-todo:TodoAccuracy"],
      registered,
      [todo({ enabled: false })],
    );
    expect(missing.map((item) => item.reason)).toEqual(["disabled"]);
  });

  it("takes a class name saved before ids when one component has it", () => {
    const withIds = new Set([...registered, "a:Twin", "b:Twin", "a:Solo"]);
    expect(unavailableComponents(["Solo"], withIds, [])).toEqual([]);
    expect(
      unavailableComponents(["Twin"], withIds, []).map((item) => item.name),
    ).toEqual(["Twin"]);
  });

  it("names each missing component once", () => {
    expect(
      unavailableComponents(["TodoAccuracy", "TodoAccuracy"], registered, []),
    ).toHaveLength(1);
  });
});

describe("the reason and the way back", () => {
  it("one sentence per plugin, naming its missing components", () => {
    const missing = unavailableComponents(
      ["TodoDummyClassifier", "TodoAccuracy", "GoneModel"],
      registered,
      [todo({ enabled: false })],
    );
    const text = unavailableText(t, missing);
    expect(text).toContain(
      JSON.stringify({
        key: "plugins:unavailable.disabled",
        names: "TodoDummyClassifier, TodoAccuracy",
        count: 2,
        plugin: "Plugin Todo",
      }),
    );
    expect(text).toContain('"key":"plugins:unavailable.uninstalled"');
  });

  it("names a component once when several runs miss it (run all)", () => {
    const perRun = unavailableComponents(["TodoAccuracy"], registered, [
      todo({ enabled: false }),
    ]);
    const text = unavailableText(t, [...perRun, ...perRun]);
    expect(text).toContain('"names":"TodoAccuracy","count":1');
  });
});

// What decides right before results are deleted.
describe("checkUnavailable reads the registry now", () => {
  beforeEach(() => {
    getComponents.mockReset();
    getInstalledPlugins.mockReset();
  });

  it("uses a fresh read, not what this window saw before", async () => {
    getComponents.mockResolvedValueOnce([{ name: "TodoAccuracy" }]);
    getInstalledPlugins.mockResolvedValueOnce([todo()]);
    expect(await checkUnavailable(["TodoAccuracy"])).toEqual([]);

    // Disabled elsewhere (another tab, the API), the next check sees it.
    getComponents.mockResolvedValueOnce([]);
    getInstalledPlugins.mockResolvedValueOnce([todo({ enabled: false })]);
    const missing = await checkUnavailable(["TodoAccuracy"]);
    expect(missing.map((item) => item.reason)).toEqual(["disabled"]);
  });

  it("shares a read already on its way (run all reads once)", async () => {
    getComponents.mockResolvedValue([{ name: "Accuracy" }]);
    getInstalledPlugins.mockResolvedValue([]);
    await Promise.all([
      checkUnavailable(["Accuracy"]),
      checkUnavailable(["Accuracy"]),
      checkUnavailable(["Accuracy"]),
    ]);
    expect(getComponents).toHaveBeenCalledTimes(1);
  });

  it("refuses when the registry can't be read: nothing is deleted", async () => {
    const snackbar = jest.fn();
    jest.spyOn(console, "error").mockImplementation(() => {});
    getComponents.mockRejectedValueOnce(new Error("offline"));
    getInstalledPlugins.mockResolvedValueOnce([]);
    expect(await confirmAvailable(["Accuracy"], t, snackbar)).toBe(false);
    expect(snackbar.mock.calls[0][0]).toContain("unavailable.checkFailed");
    console.error.mockRestore();
  });

  it("says why when something is missing, and lets it go on otherwise", async () => {
    const snackbar = jest.fn();
    getComponents.mockResolvedValue([{ name: "Accuracy" }]);
    getInstalledPlugins.mockResolvedValue([]);
    expect(await confirmAvailable(["TodoAccuracy"], t, snackbar)).toBe(false);
    expect(snackbar.mock.calls[0][0]).toContain("unavailable.uninstalled");
    expect(await confirmAvailable(["Accuracy"], t, snackbar)).toBe(true);
  });
});
