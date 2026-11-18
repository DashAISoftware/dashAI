jest.mock("./api");

import api from "./api";
import { downloadComponent, getComponents } from "./component";

describe("component download api", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("posts to the download endpoint and returns the job id", async () => {
    (api.post as jest.Mock).mockResolvedValue({ data: { id: "job-1" } });

    const result = await downloadComponent("OpusMtEnRoaTransformer");
    expect(api.post).toHaveBeenCalledWith(
      "/v1/component/OpusMtEnRoaTransformer/download",
    );
    expect(result).toEqual({ id: "job-1" });
  });
});

describe("component catalog api", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (api.get as jest.Mock).mockResolvedValue({ data: [] });
  });

  it("asks for the session catalog only when told to", async () => {
    await getComponents({
      selectTypes: ["Converter"],
      dataKind: "dataset",
      inSession: true,
    });
    expect((api.get as jest.Mock).mock.calls[0][1].params).toEqual({
      select_types: ["Converter"],
      data_kind: "dataset",
      in_session: true,
    });
  });

  it("leaves in_session out by default", async () => {
    await getComponents({ selectTypes: ["Converter"], dataKind: "dataset" });
    expect((api.get as jest.Mock).mock.calls[0][1].params).toEqual({
      select_types: ["Converter"],
      data_kind: "dataset",
    });
  });
});
