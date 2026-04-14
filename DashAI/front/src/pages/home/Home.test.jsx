import React from "react";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import Home from "./Home";

describe("Home page", () => {
  it("renders without crashing", () => {
    renderWithProviders(<Home />);
  });

  it("renders all four module cards", () => {
    renderWithProviders(<Home />);
    expect(screen.getAllByText(/datasets/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/models/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/generative/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/plugins/i).length).toBeGreaterThan(0);
  });

  it("renders sidebar with Resources section", () => {
    renderWithProviders(<Home />);
    // The sidebar label key resolves to "Resources" or "Recursos"
    expect(screen.getByText(/resources|recursos/i)).toBeInTheDocument();
  });
});
