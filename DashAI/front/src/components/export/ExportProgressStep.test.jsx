import React from "react";
import { fireEvent, screen } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import ExportProgressStep from "./ExportProgressStep";

const ROW = {
  id: 7,
  dataset_id: 4,
  dataset_name: "energy",
  exporter_name: "OpenMLDatasetExporter",
  status: "uploading",
  remote_id: null,
  remote_url: null,
  error_message: null,
};

const renderStep = (row, props = {}) => {
  const handlers = {
    onPlatformClick: jest.fn(),
    onDatasetClick: jest.fn(),
    onRetry: jest.fn(),
  };
  renderWithProviders(
    <ExportProgressStep
      exportRow={row}
      platformName="OpenML"
      loading={false}
      notFound={false}
      {...handlers}
      {...props}
    />,
  );
  return handlers;
};

describe("ExportProgressStep", () => {
  it("shows the phase the export is in", () => {
    renderStep(ROW);

    expect(screen.getByText("Publishing on OpenML")).toBeInTheDocument();
    expect(
      screen.getByText("Uploading the dataset to OpenML..."),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Try again" }),
    ).not.toBeInTheDocument();
  });

  it("links to the published dataset", () => {
    renderStep({
      ...ROW,
      status: "published",
      remote_id: "533",
      remote_url: "https://test.openml.org/d/533",
    });

    expect(screen.getByText("Dataset published on OpenML")).toBeInTheDocument();
    expect(screen.getByText("energy · ID 533")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "View on OpenML" }),
    ).toHaveAttribute("href", "https://test.openml.org/d/533");
  });

  it("explains a failure and offers to try again", () => {
    const { onRetry } = renderStep({
      ...ROW,
      status: "error",
      error_message: "Invalid symbols in description",
    });

    expect(
      screen.getByText("The dataset could not be published on OpenML"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Invalid symbols in description"),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalled();
  });

  it("goes back to the exported dataset", () => {
    const { onDatasetClick } = renderStep(ROW);

    fireEvent.click(
      screen.getByRole("button", { name: "Back to the dataset" }),
    );

    expect(onDatasetClick).toHaveBeenCalled();
  });

  it("says when the export does not exist", () => {
    renderStep(null, { notFound: true });

    expect(screen.getByText("This export was not found.")).toBeInTheDocument();
  });
});
