import React from "react";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import ManualInputForm from "./ManualInputForm";

const types = {
  SepalWidthCm: { type: "Float", dtype: "float64" },
  SepalLengthCm: { type: "Float", dtype: "float64" },
};
const sample = { SepalWidthCm: [3.5, 3.0], SepalLengthCm: [5.1, 4.9] };

describe("ManualInputForm", () => {
  it("does not break on a column the sample does not have", () => {
    // A converter's output (bin_SepalLengthCm) is in no dataset sample. The
    // callers hand the raw columns, but one that does not must not take the
    // whole page down with it.
    renderWithProviders(
      <ManualInputForm
        types={types}
        sample={sample}
        inputColumns={["bin_SepalLengthCm", "SepalWidthCm"]}
        manualInputData={[]}
        setManualInputData={jest.fn()}
      />,
    );

    expect(screen.getByText("SepalWidthCm")).toBeInTheDocument();
  });
});
