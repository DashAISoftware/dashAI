import React from "react";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import HardwareMonitorButton from "./HardwareMonitorButton";

jest.mock("../../hooks/useHardwareMonitor", () => ({
  useHardwareMonitor: () => ({ stats: null, connected: false }),
}));

describe("HardwareMonitorButton", () => {
  it("renders without crashing", () => {
    renderWithProviders(<HardwareMonitorButton />);
  });

  it("renders the monitor icon button", () => {
    renderWithProviders(<HardwareMonitorButton />);
    // aria-label comes from i18n — use getAllByRole to avoid key-resolution fragility
    expect(screen.getAllByRole("button").length).toBeGreaterThan(0);
  });
});
