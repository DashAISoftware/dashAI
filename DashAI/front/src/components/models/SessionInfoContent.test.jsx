import React from "react";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import i18n from "../../utils/i18n";
import { getComponents } from "../../api/component";
import SessionInfoContent from "./SessionInfoContent";

/*
 * The split summary a session's info shows, pinned before the splits payload
 * and its reading move behind a backend endpoint.
 */

jest.mock("../../api/component", () => ({ getComponents: jest.fn() }));

const TASK_METADATA = {
  column_roles: [
    { name: "features", label: "Features" },
    { name: "target", label: "Target" },
  ],
  io_roles: { inputs: ["features"], outputs: ["target"] },
};

const baseSession = (splits) => ({
  id: 3,
  name: "session",
  dataset_id: 1,
  task_name: "TabularClassificationTask",
  column_roles: {
    features: { columns: ["a", "b"] },
    target: { columns: ["y"] },
  },
  splits,
  created: "2026-01-02T03:04:05",
  last_modified: "2026-01-02T03:04:05",
  preprocessing: { steps: [] },
});

const t = (key) => i18n.t(key);

// The [label, value] pairs of the session configuration card, in order.
const configRows = () => {
  const heading = screen.getByText(t("models:label.sessionConfiguration"));
  const list = heading.nextElementSibling;
  return Array.from(list.children).map((card) => {
    const [header, body] = card.children;
    return [header.textContent, body.textContent];
  });
};

const renderInfo = async (splits) => {
  renderWithProviders(
    <SessionInfoContent
      session={baseSession(splits)}
      datasets={[{ id: 1, name: "iris" }]}
      tasks={[]}
    />,
  );
  // The columns of each role arrive with the task metadata.
  await waitFor(() => expect(configRows()[0]).toEqual(["Features", "a, b"]));
  return configRows();
};

// One row per role, labelled as the task labels it.
const COLUMN_ROWS = [
  ["Features", "a, b"],
  ["Target", "y"],
];

beforeEach(() => {
  getComponents.mockReset();
  getComponents.mockImplementation(async (args) => {
    if (args.model) return { metadata: TASK_METADATA };
    return [];
  });
});

describe("SessionInfoContent split summary", () => {
  it("uses the English texts the rows below are written with", () => {
    expect(t("experiments:label.splitType")).toBe("Split type");
  });

  it("random holdout: split type, the three proportions, shuffle, stratify and seed", async () => {
    const rows = await renderInfo({
      splitter_name: "HoldoutSplitter",
      splitType: "random",
      train: 0.6,
      validation: 0.2,
      test: 0.2,
      shuffle: true,
      stratify: false,
      random_state: 42,
    });

    expect(rows).toEqual([
      ...COLUMN_ROWS,
      ["Split type", "Random"],
      ["Train", "0.6"],
      ["Validation", "0.2"],
      ["Test", "0.2"],
      ["Shuffle", "Yes"],
      ["Stratify", "No"],
      ["Seed", "42"],
    ]);
  });

  it("random holdout stored as a JSON string with the legacy seed key", async () => {
    const rows = await renderInfo(
      JSON.stringify({
        splitType: "random",
        train: 0.7,
        validation: 0,
        test: 0.3,
        shuffle: false,
        seed: 5,
      }),
    );

    expect(rows).toEqual([
      ...COLUMN_ROWS,
      ["Split type", "Random"],
      ["Train", "0.7"],
      ["Validation", "0"],
      ["Test", "0.3"],
      ["Shuffle", "No"],
      ["Stratify", "No"],
      ["Seed", "5"],
    ]);
  });

  it("random holdout without a seed shows the text undefined", async () => {
    const rows = await renderInfo({
      splitter_name: "HoldoutSplitter",
      splitType: "random",
      train: 0.6,
      validation: 0.2,
      test: 0.2,
    });

    expect(rows.slice(-3)).toEqual([
      ["Shuffle", "No"],
      ["Stratify", "No"],
      ["Seed", "undefined"],
    ]);
  });

  it("manual holdout: split type and the row count of each partition", async () => {
    const rows = await renderInfo({
      splitter_name: "HoldoutSplitter",
      splitType: "manual",
      shuffle: true,
      splitted_indexes: {
        train_indexes: [0, 1, 2, 3, 4, 5],
        test_indexes: [8, 9],
        val_indexes: [6, 7, 10],
      },
    });

    expect(rows).toEqual([
      ...COLUMN_ROWS,
      ["Split type", "Manual"],
      ["Train", "6"],
      ["Validation", "3"],
      ["Test", "2"],
    ]);
  });

  it("manual holdout stored with the legacy indexes under the partition names", async () => {
    const rows = await renderInfo({
      splitType: "manual",
      train: [0, 1, 2],
      validation: [],
      test: [3],
    });

    expect(rows).toEqual([
      ...COLUMN_ROWS,
      ["Split type", "Manual"],
      ["Train", "3"],
      ["Validation", "0"],
      ["Test", "1"],
    ]);
  });

  it("predefined holdout: split type and the row count of each partition", async () => {
    const rows = await renderInfo({
      splitter_name: "HoldoutSplitter",
      splitType: "predefined",
      splitted_indexes: {
        train_indexes: [0, 1, 2, 3, 4, 5, 6],
        test_indexes: [7, 8, 9],
        val_indexes: [],
      },
    });

    expect(rows).toEqual([
      ...COLUMN_ROWS,
      ["Split type", "Predefined"],
      ["Train", "7"],
      ["Validation", "0"],
      ["Test", "3"],
    ]);
  });

  it("cv: split type, number of folds and seed, and nothing about test_size", async () => {
    const rows = await renderInfo({
      splitter_name: "KFoldSplitter",
      splitType: "cv",
      n_splits: 5,
      test_size: 0.2,
      shuffle: true,
      random_state: 0,
    });

    expect(rows).toEqual([
      ...COLUMN_ROWS,
      ["Split type", "Cross-Validation"],
      ["Number of Folds (k)", "5"],
      ["Seed", "0"],
    ]);
  });

  it("cv with repeats and a group column: both are listed before the seed", async () => {
    const rows = await renderInfo({
      splitter_name: "GroupKFoldSplitter",
      splitType: "cv",
      n_splits: 4,
      n_repeats: 2,
      group_column: "patient",
      random_state: 1,
    });

    expect(rows).toEqual([
      ...COLUMN_ROWS,
      ["Split type", "Cross-Validation"],
      ["Number of Folds (k)", "4"],
      ["Number of Repeats", "2"],
      ["Column to Group By", "patient"],
      ["Seed", "1"],
    ]);
  });

  it("cv without n_splits nor seed: only the split type and an undefined seed", async () => {
    const rows = await renderInfo({ splitType: "cv" });

    expect(rows).toEqual([
      ...COLUMN_ROWS,
      ["Split type", "Cross-Validation"],
      ["Seed", "undefined"],
    ]);
  });

  it("no splitType (full strategy, empty splits): no split rows at all", async () => {
    expect(await renderInfo({})).toEqual(COLUMN_ROWS);
  });

  it("splits that are not valid JSON: no split rows at all", async () => {
    expect(await renderInfo("{not json")).toEqual(COLUMN_ROWS);
  });

  it("a strategy without a form of its own: the splitter and its parameters, as its schema names them", async () => {
    getComponents.mockImplementation(async (args) => {
      if (args.model === "RollingOriginSplitter") {
        return {
          name: "RollingOriginSplitter",
          display_name: "Rolling origin",
          schema: {
            properties: {
              horizon: { title: "Horizon" },
              n_origins: { title: "Validation origins" },
            },
          },
        };
      }
      if (args.model) return { metadata: TASK_METADATA };
      return [];
    });

    const rows = await renderInfo({
      splitter_name: "RollingOriginSplitter",
      horizon: 3,
      n_origins: 4,
    });

    await waitFor(() =>
      expect(configRows()).toEqual([
        ...COLUMN_ROWS,
        ["Splitter", "Rolling origin"],
        ["Horizon", "3"],
        ["Validation origins", "4"],
      ]),
    );
    expect(rows.slice(0, 2)).toEqual(COLUMN_ROWS);
  });
});
