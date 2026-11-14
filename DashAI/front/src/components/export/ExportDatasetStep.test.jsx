import React from "react";
import { fireEvent, screen } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import ExportDatasetStep from "./ExportDatasetStep";

const compatibility = (status, unsupported = []) => ({
  status,
  messages: [],
  unsupported_columns: unsupported,
});

const IRIS = {
  id: 1,
  name: "iris",
  total_rows: 150,
  total_columns: 5,
  compatibility: compatibility("compatible"),
};
const CATALOG = {
  id: 2,
  name: "catalog",
  total_rows: 500,
  total_columns: 6,
  compatibility: compatibility("warning", ["photo"]),
};
const MNIST = {
  id: 3,
  name: "spanish-mnist",
  total_rows: 800,
  total_columns: 2,
  compatibility: compatibility("incompatible", ["image"]),
};

const renderStep = (props = {}) => {
  const handlers = {
    onSelect: jest.fn(),
    onBack: jest.fn(),
    onNext: jest.fn(),
  };
  renderWithProviders(
    <ExportDatasetStep
      platformName="OpenML"
      datasets={[IRIS, CATALOG, MNIST]}
      loading={false}
      error={false}
      selected={null}
      {...handlers}
      {...props}
    />,
  );
  return handlers;
};

const nextButton = () => screen.getByRole("button", { name: /next/i });

describe("ExportDatasetStep", () => {
  it("shows how each dataset fits the platform", () => {
    renderStep();

    expect(screen.getByText("Compatible")).toBeInTheDocument();
    expect(
      screen.getByText("The columns photo will not be sent"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Not compatible: without image/),
    ).toBeInTheDocument();
    expect(
      screen.getByText("3 datasets · 2 can be exported to OpenML"),
    ).toBeInTheDocument();
  });

  it("selects a dataset the platform accepts, even with a warning", () => {
    const { onSelect } = renderStep();

    fireEvent.click(screen.getByText("catalog"));

    expect(onSelect).toHaveBeenCalledWith(CATALOG);
  });

  it("does not select an incompatible dataset", () => {
    const { onSelect } = renderStep();

    fireEvent.click(screen.getByText("spanish-mnist"));

    expect(onSelect).not.toHaveBeenCalled();
    expect(screen.getByRole("radio", { name: "spanish-mnist" })).toBeDisabled();
  });

  it("continues only once a dataset is selected", () => {
    renderStep();
    expect(nextButton()).toBeDisabled();
  });

  it("continues with the selected dataset", () => {
    const { onNext } = renderStep({ selected: IRIS });

    fireEvent.click(nextButton());

    expect(onNext).toHaveBeenCalledWith(IRIS);
  });

  it("filters the list by name", () => {
    renderStep();

    fireEvent.change(screen.getByRole("textbox", { name: /search dataset/i }), {
      target: { value: "iri" },
    });

    expect(screen.getByText("iris")).toBeInTheDocument();
    expect(screen.queryByText("catalog")).not.toBeInTheDocument();
  });

  it("says when the list could not be loaded", () => {
    renderStep({ datasets: [], error: true });

    expect(
      screen.getByText("The dataset list could not be loaded."),
    ).toBeInTheDocument();
  });

  it("says when no dataset is ready", () => {
    renderStep({ datasets: [] });

    expect(
      screen.getByText("No datasets are ready to export."),
    ).toBeInTheDocument();
  });

  it("goes back to the platform step", () => {
    const { onBack } = renderStep();

    fireEvent.click(screen.getAllByRole("button", { name: /back/i })[0]);

    expect(onBack).toHaveBeenCalled();
  });
});
