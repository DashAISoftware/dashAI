import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import QueryTransformationPicker from "./QueryTransformationPicker";
import useQueryTransformationOptions from "../../../hooks/useQueryTransformationOptions";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key) => key }),
}));
jest.mock("../../../hooks/useQueryTransformationOptions", () => ({
  __esModule: true,
  default: jest.fn(),
}));
jest.mock("./PresetCardList", () => ({
  __esModule: true,
  default: ({ presets, onSelect }) => (
    <div>
      {presets.map((preset) => (
        <button key={preset.key} type="button" onClick={() => onSelect(preset)}>
          {preset.key}
        </button>
      ))}
    </div>
  ),
}));
jest.mock(
  "../../../pages/generative/RAGSession/advanced/QueryTransformationAdvancedModal",
  () => ({
    __esModule: true,
    default: ({ setModel }) => (
      <div>
        <button
          type="button"
          onClick={() =>
            setModel({
              component: "LLMQueryExpander",
              params: {
                llm_model: { component: "Missing", params: {} },
                prompt: { component: "Prompt", params: {} },
              },
            })
          }
        >
          commit-missing
        </button>
        <button
          type="button"
          onClick={() =>
            setModel({
              component: "LLMQueryExpander",
              params: {
                llm_model: { component: "Downloaded", params: {} },
                prompt: { component: "Prompt", params: {} },
              },
            })
          }
        >
          commit-downloaded
        </button>
      </div>
    ),
  }),
);

const TRANSFORMER = {
  name: "LLMQueryExpander",
  display_name: "Expander",
  description: "d",
  metadata: { technique: "expansion" },
  schema: {
    properties: {
      llm_model: { placeholder: { component: "Downloaded" } },
    },
  },
};
const PROMPTS = [
  { name: "Prompt", metadata: { technique: "expansion", variant: "default" } },
];

const mockOptions = (overrides = {}) =>
  useQueryTransformationOptions.mockReturnValue({
    transformers: [TRANSFORMER],
    prompts: PROMPTS,
    generators: [
      { name: "Downloaded", downloaded: true },
      { name: "Missing", downloaded: false },
    ],
    loading: false,
    loadError: null,
    ...overrides,
  });

describe("QueryTransformationPicker", () => {
  it("enables the stage with a downloaded model and the default prompt", async () => {
    mockOptions();
    const onChange = jest.fn();
    render(<QueryTransformationPicker value={null} onChange={onChange} />);

    await userEvent.click(
      screen.getByRole("button", { name: "LLMQueryExpander" }),
    );

    expect(onChange).toHaveBeenCalledWith({
      component: "LLMQueryExpander",
      params: {
        llm_model: { component: "Downloaded", params: {} },
        prompt: { component: "Prompt", params: { language: "en" } },
      },
    });
  });

  it("explains why it cannot be enabled when no model is downloaded", async () => {
    mockOptions({ generators: [{ name: "Missing", downloaded: false }] });
    const onChange = jest.fn();
    render(<QueryTransformationPicker value={null} onChange={onChange} />);

    await userEvent.click(
      screen.getByRole("button", { name: "LLMQueryExpander" }),
    );

    expect(onChange).not.toHaveBeenCalled();
    expect(
      screen.getByText(
        "generative:rag.config.queryTransformation.needsDownloadedModel",
      ),
    ).toBeInTheDocument();
  });

  it("refuses an advanced edit that picks a model that is not downloaded", async () => {
    mockOptions();
    const onChange = jest.fn();
    render(
      <QueryTransformationPicker
        value={{ component: "LLMQueryExpander", params: {} }}
        onChange={onChange}
      />,
    );

    await userEvent.click(
      screen.getByRole("button", { name: "commit-missing" }),
    );

    expect(onChange).not.toHaveBeenCalled();
  });

  it("persists an advanced edit that picks a downloaded model", async () => {
    mockOptions();
    const onChange = jest.fn();
    render(
      <QueryTransformationPicker
        value={{ component: "LLMQueryExpander", params: {} }}
        onChange={onChange}
      />,
    );

    await userEvent.click(
      screen.getByRole("button", { name: "commit-downloaded" }),
    );

    expect(onChange).toHaveBeenCalledTimes(1);
  });

  it("turns the stage off without waiting for the options", async () => {
    mockOptions({ loading: true });
    const onChange = jest.fn();
    render(
      <QueryTransformationPicker
        value={{ component: "LLMQueryExpander", params: {} }}
        onChange={onChange}
      />,
    );

    await userEvent.click(screen.getByRole("switch"));

    expect(onChange).toHaveBeenCalledWith(null);
  });

  it("shows the load failure and keeps the switch off", () => {
    mockOptions({ loadError: "boom" });
    render(<QueryTransformationPicker value={null} onChange={jest.fn()} />);

    expect(
      screen.getByText("generative:rag.config.queryTransformation.loadFailed"),
    ).toBeInTheDocument();
    expect(screen.getByRole("switch")).toBeDisabled();
  });
});
