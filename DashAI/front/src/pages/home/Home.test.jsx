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
    expect(screen.getByText(/datasets/i)).toBeInTheDocument();
    expect(screen.getByText(/models/i)).toBeInTheDocument();
    expect(screen.getByText(/generative/i)).toBeInTheDocument();
    expect(screen.getByText(/plugins/i)).toBeInTheDocument();
  });

  it("renders sidebar with Resources section", () => {
    renderWithProviders(<Home />);
    // The sidebar label key resolves to "Resources" or "Recursos"
    expect(screen.getByText(/resources|recursos/i)).toBeInTheDocument();
  });
});
