import React from "react";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import { TourButton } from "./TourButton";
import { TourProvider } from "./TourProvider";
import { TOUR_KEYS } from "../../constants/tours";

describe("TourButton", () => {
  it("renders without crashing", () => {
    renderWithProviders(
      <TourProvider tourKey={TOUR_KEYS.HOME}>
        <TourButton tourKey={TOUR_KEYS.HOME} />
      </TourProvider>
    );
  });

  it("renders the help icon button", () => {
    renderWithProviders(
      <TourProvider tourKey={TOUR_KEYS.HOME}>
        <TourButton tourKey={TOUR_KEYS.HOME} />
      </TourProvider>
    );
    expect(screen.getByRole("button")).toBeInTheDocument();
  });
});
