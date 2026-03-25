import React from "react";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../test-utils/renderWithProviders";
import HomeButton from "./HomeButton";
import { Science as ScienceIcon } from "@mui/icons-material";

const defaultProps = {
  title: "Models",
  description: "Train and compare models.",
  to: "/app/models",
  Icon: ScienceIcon,
  accent: "#1d9e75",
  accentDim: "rgba(29,158,117,0.10)",
  accentBorder: "rgba(29,158,117,0.22)",
  accentGlow: "rgba(29,158,117,0.04)",
  tag: "Comenzar",
  chips: ["classification", "regression"],
};

describe("HomeButton (module card)", () => {
  it("renders without crashing", () => {
    renderWithProviders(<HomeButton {...defaultProps} />);
  });

  it("renders the title", () => {
    renderWithProviders(<HomeButton {...defaultProps} />);
    expect(screen.getByText("Models")).toBeInTheDocument();
  });

  it("renders chip labels", () => {
    renderWithProviders(<HomeButton {...defaultProps} />);
    expect(screen.getByText("classification")).toBeInTheDocument();
  });

  it("renders a link to the correct route", () => {
    renderWithProviders(<HomeButton {...defaultProps} />);
    expect(screen.getByRole("link")).toHaveAttribute("href", "/app/models");
  });
});
