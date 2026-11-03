jest.mock("./api");

import api from "./api";
import { createPrediction, getPredictionSplits } from "./predict";

describe("predict api", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("createPrediction", () => {
    it("posts the run and the dataset, with no split", async () => {
      (api.post as jest.Mock).mockResolvedValue({ data: { id: 11 } });

      const result = await createPrediction(3, 7);

      expect(api.post).toHaveBeenCalledTimes(1);
      expect(api.post).toHaveBeenCalledWith("/v1/predict/", {
        run_id: 3,
        dataset_id: 7,
        split: undefined,
      });
      const body = (api.post as jest.Mock).mock.calls[0][1];
      expect(Object.keys(body).sort()).toEqual([
        "dataset_id",
        "run_id",
        "split",
      ]);
      expect(result).toEqual({ id: 11 });
    });

    it("posts a horizon, and no dataset nor split, for a forecast", async () => {
      (api.post as jest.Mock).mockResolvedValue({
        data: { id: 14, unevaluated_steps: 2 },
      });

      const result = await createPrediction(3, null, null, 5);

      expect(api.post).toHaveBeenCalledWith("/v1/predict/", {
        run_id: 3,
        dataset_id: null,
        split: null,
        horizon: 5,
      });
      expect(result).toEqual({ id: 14, unevaluated_steps: 2 });
    });

    it("posts the split the prediction targets", async () => {
      (api.post as jest.Mock).mockResolvedValue({ data: { id: 12 } });

      await createPrediction(3, 7, "test");

      expect(api.post).toHaveBeenCalledWith("/v1/predict/", {
        run_id: 3,
        dataset_id: 7,
        split: "test",
      });
    });

    it("posts a null dataset for a manual prediction", async () => {
      (api.post as jest.Mock).mockResolvedValue({ data: { id: 13 } });

      // PredictionModal (JS) passes null for the dataset, outside the TS type.
      await createPrediction(3, null as unknown as undefined, null);

      expect(api.post).toHaveBeenCalledWith("/v1/predict/", {
        run_id: 3,
        dataset_id: null,
        split: null,
      });
      const body = (api.post as jest.Mock).mock.calls[0][1];
      expect(Object.keys(body).sort()).toEqual([
        "dataset_id",
        "run_id",
        "split",
      ]);
    });
  });

  describe("getPredictionSplits", () => {
    it("gets the run's splits and renames the training dataset id", async () => {
      (api.get as jest.Mock).mockResolvedValue({
        data: {
          splits: [
            { name: "all", rows: 100 },
            { name: "test", rows: 20 },
          ],
          training_dataset_id: 5,
        },
      });

      const result = await getPredictionSplits(9);

      expect(api.get).toHaveBeenCalledWith("/v1/predict/splits/9");
      expect(result).toEqual({
        splits: [
          { name: "all", rows: 100 },
          { name: "test", rows: 20 },
        ],
        trainingDatasetId: 5,
        // A run of a task that predicts rows measured no horizon.
        horizon: null,
      });
    });

    it("passes an empty split list and a null training dataset through", async () => {
      (api.get as jest.Mock).mockResolvedValue({
        data: { splits: [], training_dataset_id: null },
      });

      const result = await getPredictionSplits(9);

      expect(result).toEqual({
        splits: [],
        trainingDatasetId: null,
        horizon: null,
      });
    });
  });

  it("getPredictionSplits gives the horizon the run measured", async () => {
    (api.get as jest.Mock).mockResolvedValue({
      data: { splits: [], training_dataset_id: 2, horizon: 3 },
    });

    expect(await getPredictionSplits(9)).toEqual({
      splits: [],
      trainingDatasetId: 2,
      horizon: 3,
    });
  });
});
