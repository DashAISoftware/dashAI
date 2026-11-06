jest.mock("./api");

import api from "./api";
import {
  createModelSession,
  getPreprocessingStructure,
  validateColumns,
} from "./modelSession";

const ROLES = {
  features: [{ kind: "group" as const, step: 0 }],
  target: [{ kind: "raw" as const, name: "label" }],
};

describe("createModelSession", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (api.post as jest.Mock).mockResolvedValue({ data: { id: "session-1" } });
  });

  it("sends the columns by role and the preprocessing", async () => {
    await createModelSession(
      1,
      "TabularClassificationTask",
      "session-1",
      ROLES,
      [],
      [],
      [],
      "holdout",
      JSON.parse("{}"),
      [
        {
          converter: "Binarizer",
          params: { threshold: 0.5 },
          scope: [{ kind: "raw", name: "age" }],
        },
      ],
    );

    expect(api.post).toHaveBeenCalledWith(
      "/v1/model-session/",
      expect.objectContaining({
        column_roles: ROLES,
        preprocessing: [
          {
            converter: "Binarizer",
            params: { threshold: 0.5 },
            scope: [{ kind: "raw", name: "age" }],
          },
        ],
      }),
    );
  });

  it("sends none of the old column fields", async () => {
    await createModelSession(
      1,
      "TabularClassificationTask",
      "session-2",
      ROLES,
      [],
      [],
      [],
      "holdout",
      JSON.parse("{}"),
    );

    const body = (api.post as jest.Mock).mock.calls[0][1];
    expect(body.preprocessing).toEqual([]);
    expect(body).not.toHaveProperty("input_columns");
    expect(body).not.toHaveProperty("output_columns");
    expect(body).not.toHaveProperty("input_column_refs");
  });
});

describe("validateColumns", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (api.post as jest.Mock).mockResolvedValue({ data: {} });
  });

  it("sends the columns by role", async () => {
    await validateColumns("TabularClassificationTask", 1, ROLES);

    expect(api.post).toHaveBeenCalledWith(
      "/v1/model-session/validation",
      expect.objectContaining({
        task_name: "TabularClassificationTask",
        dataset_id: 1,
        column_roles: ROLES,
      }),
    );
  });
});

describe("getPreprocessingStructure", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (api.post as jest.Mock).mockResolvedValue({ data: {} });
  });

  it("sends the task and the original columns by role", async () => {
    await getPreprocessingStructure({
      datasetId: 1,
      taskName: "TabularClassificationTask",
      columnRoles: { features: ["age"], target: ["label"] },
      steps: [],
    });

    expect(api.post).toHaveBeenCalledWith(
      "/v1/model-session/preprocessing/structure",
      {
        dataset_id: 1,
        task_name: "TabularClassificationTask",
        column_roles: { features: ["age"], target: ["label"] },
        steps: [],
      },
    );
  });
});
