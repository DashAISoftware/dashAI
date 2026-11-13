import React from "react";
import { fireEvent, screen } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import ExportPlatformStep from "./ExportPlatformStep";
import { setCredentialStatus } from "../credentials/credentialStatus";

jest.mock("../../api/credentials", () => ({
  getCredentials: jest.fn(() => Promise.resolve([])),
  authenticateCredential: jest.fn(),
  deleteCredential: jest.fn(),
}));

const OPENML = {
  name: "OpenMLDatasetExporter",
  type: "DatasetExporter",
  display_name: "OpenML",
  description: "Publish the dataset on OpenML.",
  required_credentials: ["OpenMLCredential"],
  optional_credentials: [],
};

const renderStep = (props = {}) => {
  const handlers = {
    onSelect: jest.fn(),
    onBack: jest.fn(),
    onNext: jest.fn(),
  };
  renderWithProviders(
    <ExportPlatformStep
      exporters={[OPENML]}
      selected={null}
      {...handlers}
      {...props}
    />,
  );
  return handlers;
};

const nextButton = () => screen.getByRole("button", { name: /next/i });

describe("ExportPlatformStep", () => {
  // Seeding the shared credential cache marks it as loaded, so rendering never
  // starts the background fetch whose late update React would warn about.
  beforeEach(() => setCredentialStatus("OpenMLCredential", false));

  it("lists the export platforms and reports a click", () => {
    const { onSelect } = renderStep();

    fireEvent.click(screen.getByText("OpenML"));

    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({ name: "OpenMLDatasetExporter" }),
    );
  });

  it("does not continue before a platform is selected", () => {
    renderStep();
    expect(nextButton()).toBeDisabled();
  });

  it("does not continue while the platform credential is missing", () => {
    renderStep({ selected: OPENML });

    expect(nextButton()).toBeDisabled();
    expect(screen.getByText(/OpenML credential/i)).toBeInTheDocument();
  });

  it("continues with the selected platform once its credential is set", () => {
    setCredentialStatus("OpenMLCredential", true);
    const { onNext } = renderStep({ selected: OPENML });

    fireEvent.click(nextButton());

    expect(onNext).toHaveBeenCalledWith(OPENML);
  });

  it("goes back to the data module", () => {
    const { onBack } = renderStep();

    fireEvent.click(screen.getAllByRole("button", { name: /back/i })[0]);

    expect(onBack).toHaveBeenCalled();
  });
});
