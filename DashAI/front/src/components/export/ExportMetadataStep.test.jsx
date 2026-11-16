import React from "react";
import { fireEvent, screen } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import ExportMetadataStep from "./ExportMetadataStep";

const COLUMNS = ["id", "price", "photo", "category"];
const SAMPLE = {
  id: [1, 2],
  price: [9.5, 12],
  photo: ["<bytes>", "<bytes>"],
  category: ["a", "b"],
};
const COLUMN_FIELDS = [
  { key: "label_column", title: "Label column", multiple: false },
  { key: "skipped_columns", title: "Skipped columns", multiple: true },
];

const renderStep = (props = {}) => {
  const handlers = {
    onPlatformClick: jest.fn(),
    onBack: jest.fn(),
    onNext: jest.fn(),
  };
  renderWithProviders(
    <ExportMetadataStep
      platformName="OpenML"
      datasetName="catalog"
      columns={COLUMNS}
      sample={SAMPLE}
      unsupportedColumns={["photo"]}
      columnFields={COLUMN_FIELDS}
      columnValues={{ label_column: "category", skipped_columns: ["id"] }}
      loading={false}
      error={false}
      canContinue
      {...handlers}
      {...props}
    />,
  );
  return handlers;
};

const reviewButton = () => screen.getByRole("button", { name: /review/i });

describe("ExportMetadataStep", () => {
  it("marks each picked column with the title of its field", () => {
    renderStep();

    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("Label column")).toBeInTheDocument();
    expect(screen.getByText("Skipped columns")).toBeInTheDocument();
    expect(screen.getByText("not sent")).toBeInTheDocument();
  });

  it("hides the values of columns the platform will not receive", () => {
    renderStep();

    expect(screen.queryByText("<bytes>")).not.toBeInTheDocument();
    expect(
      screen.getByText("The columns photo will not be sent"),
    ).toBeInTheDocument();
  });

  it("shows where the user is in the breadcrumb", () => {
    const { onPlatformClick } = renderStep();

    fireEvent.click(screen.getByRole("button", { name: "OpenML" }));

    expect(onPlatformClick).toHaveBeenCalled();
    expect(screen.getByText("catalog")).toBeInTheDocument();
  });

  it("continues to the review once the form is complete", () => {
    const { onNext } = renderStep();

    fireEvent.click(reviewButton());

    expect(onNext).toHaveBeenCalled();
  });

  it("explains what is missing while the form is incomplete", () => {
    renderStep({ canContinue: false, columnValues: {} });

    expect(reviewButton()).toBeDisabled();
    expect(
      screen.getByText("Fill in the required fields to continue."),
    ).toBeInTheDocument();
  });

  it("says when the dataset could not be loaded", () => {
    renderStep({ error: true });

    expect(
      screen.getByText("The dataset could not be loaded."),
    ).toBeInTheDocument();
  });
});
