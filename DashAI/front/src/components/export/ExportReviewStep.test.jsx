import React from "react";
import { fireEvent, screen } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import ExportReviewStep from "./ExportReviewStep";

const PARAMS = {
  name: "energy",
  description: "Building energy use.",
  licence: "CC0",
  default_target_attribute: "Energy Consumption",
  ignore_attribute: ["Building ID"],
  creator: null,
  citation: "",
};
const TITLES = {
  name: "Name",
  description: "Description",
  licence: "Licence",
  default_target_attribute: "Target column",
  ignore_attribute: "Ignored columns",
  creator: "Creator",
  citation: "Citation",
};
const VALID = { loading: false, errors: [], failed: false };

const renderStep = (props = {}) => {
  const handlers = {
    onConfirmChange: jest.fn(),
    onPlatformClick: jest.fn(),
    onBack: jest.fn(),
    onPublish: jest.fn(),
  };
  renderWithProviders(
    <ExportReviewStep
      platformName="OpenML"
      datasetName="energy"
      params={PARAMS}
      fieldTitles={TITLES}
      summary={{ rows: 1000, columns: 7, sentColumns: 6, leftOut: ["photo"] }}
      validation={VALID}
      confirmed={false}
      publishing={false}
      publishError={null}
      {...handlers}
      {...props}
    />,
  );
  return handlers;
};

const publishButton = () =>
  screen.getByRole("button", { name: "Publish on OpenML" });

describe("ExportReviewStep", () => {
  it("summarizes the filled metadata and what will be sent", () => {
    renderStep();

    expect(screen.getByText("Building energy use.")).toBeInTheDocument();
    expect(screen.getByText("Energy Consumption")).toBeInTheDocument();
    expect(screen.getByText("Building ID")).toBeInTheDocument();
    expect(screen.queryByText("Creator")).not.toBeInTheDocument();
    expect(screen.queryByText("Citation")).not.toBeInTheDocument();
    expect(screen.getByText("Rows: 1000")).toBeInTheDocument();
    expect(screen.getByText("Columns sent: 6 of 7")).toBeInTheDocument();
    expect(
      screen.getByText("The columns photo will not be sent"),
    ).toBeInTheDocument();
  });

  it("asks for confirmation before publishing", () => {
    const { onConfirmChange } = renderStep();

    expect(screen.getByText("No validation errors")).toBeInTheDocument();
    expect(publishButton()).toBeDisabled();

    fireEvent.click(screen.getByRole("checkbox"));

    expect(onConfirmChange).toHaveBeenCalledWith(true);
  });

  it("publishes once the export is valid and confirmed", () => {
    const { onPublish } = renderStep({ confirmed: true });

    fireEvent.click(publishButton());

    expect(onPublish).toHaveBeenCalled();
  });

  it("shows the adjustments the platform will make without blocking", () => {
    const { onPublish } = renderStep({
      confirmed: true,
      validation: {
        loading: false,
        errors: [],
        warnings: ["The name will be published as 'Mi_dataset'."],
        failed: false,
      },
    });

    expect(
      screen.getByText("The name will be published as 'Mi_dataset'."),
    ).toBeInTheDocument();
    fireEvent.click(publishButton());
    expect(onPublish).toHaveBeenCalled();
  });

  it("lists the validation errors and blocks publishing", () => {
    renderStep({
      confirmed: true,
      validation: {
        loading: false,
        errors: ["The target column 'x' is not in the dataset."],
        failed: false,
      },
    });

    expect(
      screen.getByText("The target column 'x' is not in the dataset."),
    ).toBeInTheDocument();
    expect(publishButton()).toBeDisabled();
  });

  it("blocks publishing while the validation runs", () => {
    renderStep({
      confirmed: true,
      validation: { loading: true, errors: [], failed: false },
    });

    expect(
      screen.getByText("Validating the dataset and metadata..."),
    ).toBeInTheDocument();
    expect(publishButton()).toBeDisabled();
  });

  it("shows why publishing failed", () => {
    renderStep({ publishError: "Missing credentials: OpenMLCredential." });

    expect(
      screen.getByText("Missing credentials: OpenMLCredential."),
    ).toBeInTheDocument();
  });

  it("sends the user back to the form when the metadata was lost", () => {
    const { onBack } = renderStep({ params: null, confirmed: true });

    expect(publishButton()).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Back to the form" }));

    expect(onBack).toHaveBeenCalled();
  });
});
