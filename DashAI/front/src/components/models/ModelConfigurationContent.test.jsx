import React from "react";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import i18n from "../../utils/i18n";
import ModelConfigurationContent from "./ModelConfigurationContent";

describe("ModelConfigurationContent", () => {
  it("says which exogenous variables a run read", () => {
    renderWithProviders(
      <ModelConfigurationContent
        run={{
          parameters: { p: 1 },
          exogenous: {
            used: true,
            columns: [{ name: "promo", type: "Float" }],
            reason: null,
          },
        }}
      />,
    );

    expect(
      screen.getByText(i18n.t("models:exogenous.used", { columns: "promo" })),
    ).toBeInTheDocument();
  });

  it("says why a run did not read them", () => {
    renderWithProviders(
      <ModelConfigurationContent
        run={{
          parameters: {},
          exogenous: {
            used: false,
            columns: [{ name: "promo", type: "Float" }],
            reason: {
              key: "modelTakesNoExogenous",
              values: { model: "NaiveForecaster" },
            },
          },
        }}
      />,
    );

    expect(
      screen.getByText(
        i18n.t("models:exogenous.reason.modelTakesNoExogenous", {
          model: "NaiveForecaster",
        }),
      ),
    ).toBeInTheDocument();
  });

  it("shows nothing of them for a run without exogenous variables", () => {
    renderWithProviders(
      <ModelConfigurationContent run={{ parameters: { p: 1 } }} />,
    );

    expect(
      screen.queryByText(i18n.t("models:exogenous.title")),
    ).not.toBeInTheDocument();
  });
});
