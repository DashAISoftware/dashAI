import React from "react";
import { fireEvent, screen } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import ExportHistoryPanel from "./ExportHistoryPanel";

const EXPORTS = [
  {
    id: 2,
    exporter_name: "OpenMLDatasetExporter",
    status: "published",
    remote_id: "533",
    created: "2026-11-15T19:38:01",
  },
  {
    id: 1,
    exporter_name: "OpenMLDatasetExporter",
    status: "error",
    remote_id: null,
    created: "2026-11-15T19:30:00",
  },
];

const renderPanel = (props = {}) => {
  const onSelect = jest.fn();
  renderWithProviders(
    <ExportHistoryPanel
      datasetName="energy"
      exports={EXPORTS}
      currentId={2}
      platformLabel={() => "OpenML"}
      onSelect={onSelect}
      {...props}
    />,
  );
  return onSelect;
};

describe("ExportHistoryPanel", () => {
  it("lists every export of the dataset with its status", () => {
    renderPanel();

    expect(screen.getByText("Exports of energy")).toBeInTheDocument();
    expect(screen.getByText("OpenML · ID 533")).toBeInTheDocument();
    expect(screen.getByText("Published")).toBeInTheDocument();
    expect(screen.getByText("Error")).toBeInTheDocument();
  });

  it("opens the clicked export", () => {
    const onSelect = renderPanel();

    fireEvent.click(screen.getByText("Error"));

    expect(onSelect).toHaveBeenCalledWith(EXPORTS[1]);
  });

  it("says when the dataset has no exports", () => {
    renderPanel({ exports: [] });

    expect(
      screen.getByText("This dataset has no exports."),
    ).toBeInTheDocument();
  });
});
