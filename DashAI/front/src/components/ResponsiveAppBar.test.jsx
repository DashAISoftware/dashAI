import React from "react";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../test-utils/renderWithProviders";
import ResponsiveAppBar from "./ResponsiveAppBar";

describe("ResponsiveAppBar", () => {
  it("renders without crashing", () => {
    renderWithProviders(<ResponsiveAppBar />);
  });

  it("renders DashAI logo text", () => {
    renderWithProviders(<ResponsiveAppBar />);
    expect(screen.getByText("AI")).toBeInTheDocument();
  });

  it("renders nav links for main sections", () => {
    renderWithProviders(<ResponsiveAppBar />);
    expect(screen.getByRole("link", { name: /datasets/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /models/i })).toBeInTheDocument();
  });
});
