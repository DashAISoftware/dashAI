import React from "react";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../../test-utils/renderWithProviders";
import i18n from "../../../utils/i18n";
import splitPreviewCases from "./__fixtures__/splitPreviewCases.json";
import SplitPreview from "./SplitPreview";

/*
 * The split preview draws what the splitter computed (POST /splitter/preview),
 * and computes nothing. The answers are the shared cases' expectations, which
 * the backend gives for the same configurations.
 */

jest.mock("react-markdown", () => ({
  __esModule: true,
  default: ({ children }) => <span>{children}</span>,
}));

const t = (key, values) => i18n.t(key, values);

describe("SplitPreview draws the splitter's answer", () => {
  it.each(splitPreviewCases.map((c) => [c.name, c]))("%s", (_name, c) => {
    renderWithProviders(<SplitPreview preview={c.expected} />);

    c.expected.rows.forEach((row) => {
      const text = row.ellipsis
        ? t(`experiments:splitPreview.${row.label}`, {
            hidden: row.hidden_count,
          })
        : t(`experiments:splitPreview.${row.label}`, row.label_values);
      expect(screen.getAllByText(text).length).toBeGreaterThan(0);
    });
    c.expected.notes.forEach((note) => {
      expect(
        screen.getByText(
          t(`experiments:splitPreview.notes.${note.key}`, note.values),
        ),
      ).toBeInTheDocument();
    });
    Object.entries(c.expected.shares)
      .filter(([, share]) => share > 0.0001)
      .forEach(([role, share]) => {
        const label =
          role === "unused"
            ? t("experiments:splitPreview.unused")
            : t(`common:${role}`);
        expect(
          screen.getByText(`${label} ${Math.round(share * 100)}%`),
        ).toBeInTheDocument();
      });
  });

  it("a backtest: one bar per origin, the test and the kept model", () => {
    renderWithProviders(
      <SplitPreview
        preview={{
          rows: [
            {
              key: "origin-0",
              label: "origin",
              label_values: { index: 1 },
              segments: [
                { role: "train", fraction: 0.5 },
                { role: "validation", fraction: 0.125 },
                { role: "unused", fraction: 0.375 },
              ],
            },
            {
              key: "ellipsis",
              label: "moreOrigins",
              ellipsis: true,
              hidden_count: 8,
            },
            {
              key: "test",
              label: "testOrigin",
              label_values: {},
              segments: [
                { role: "train", fraction: 0.875 },
                { role: "test", fraction: 0.125 },
              ],
            },
            {
              key: "final",
              label: "finalFit",
              label_values: {},
              segments: [{ role: "train", fraction: 1 }],
            },
          ],
          notes: [{ key: "originsHidden", values: { total: 12 } }],
          shares: { train: 0.5, validation: 0.375, test: 0.125 },
          errors: [],
          partitions: ["validation", "test"],
        }}
      />,
    );

    expect(screen.getByText("Origin 1")).toBeInTheDocument();
    expect(screen.getByText("+8 more origins")).toBeInTheDocument();
    expect(screen.getByText("Test")).toBeInTheDocument();
    expect(screen.getByText("Final fit")).toBeInTheDocument();
    expect(
      screen.getByText(
        "12 origins in total; only the first ones and the last are drawn.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Validation 38%")).toBeInTheDocument();
  });

  it("no preview: says so, or that it is being drawn", () => {
    const { rerender } = renderWithProviders(<SplitPreview preview={null} />);
    expect(
      screen.getByText(t("experiments:splitPreview.unavailable")),
    ).toBeInTheDocument();

    rerender(<SplitPreview preview={null} loading />);
    expect(
      screen.getByText(t("experiments:splitPreview.loading")),
    ).toBeInTheDocument();
  });
});
