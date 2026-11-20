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

  describe("a parameter left empty", () => {
    const resolved = {
      season_length: {
        value: 12,
        reason: { key: "seasonFromStep", values: { step: "M" } },
      },
      lags: {
        value: 12,
        reason: { key: "lagsFromSeason", values: { season: 12 } },
      },
    };
    let language;

    beforeEach(async () => {
      language = i18n.language;
      await i18n.changeLanguage("es");
    });

    afterEach(async () => {
      await i18n.changeLanguage(language);
    });

    it("shows the value the run resolved and where it came from", () => {
      renderWithProviders(
        <ModelConfigurationContent
          run={{
            parameters: {
              lags: null,
              season_length: {
                optimize: false,
                fixed_value: null,
                lower_bound: 1,
                upper_bound: 12,
              },
            },
            resolved_parameters: resolved,
          }}
        />,
      );

      expect(
        screen.getByText("12 (según la frecuencia mensual)"),
      ).toBeInTheDocument();
      expect(screen.getByText("12 (una temporada de 12)")).toBeInTheDocument();
      expect(screen.queryByText("null")).not.toBeInTheDocument();
    });

    it("shows it also when the run left the parameter out", () => {
      renderWithProviders(
        <ModelConfigurationContent
          run={{
            parameters: {},
            resolved_parameters: { season_length: resolved.season_length },
          }}
        />,
      );

      expect(
        screen.getByText("12 (según la frecuencia mensual)"),
      ).toBeInTheDocument();
    });

    it("names the frequency when the app has no word for its step", () => {
      renderWithProviders(
        <ModelConfigurationContent
          run={{
            parameters: {},
            resolved_parameters: {
              season_length: {
                value: 4,
                reason: {
                  key: "seasonFromFrequency",
                  values: { freq: "15min" },
                },
              },
            },
          }}
        />,
      );

      expect(
        screen.getByText("4 (según la frecuencia 15min de la serie)"),
      ).toBeInTheDocument();
    });

    it("says when the lags are the minimum, not one season", () => {
      renderWithProviders(
        <ModelConfigurationContent
          run={{
            parameters: { lags: null },
            resolved_parameters: {
              lags: {
                value: 3,
                reason: {
                  key: "lagsAtLeast",
                  values: { season: 1, minimum: 3 },
                },
              },
            },
          }}
        />,
      );

      expect(
        screen.getByText("3 (el mínimo, 3: la temporada es 1)"),
      ).toBeInTheDocument();
    });
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
