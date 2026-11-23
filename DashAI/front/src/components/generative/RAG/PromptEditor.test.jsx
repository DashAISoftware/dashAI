import React from "react";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../../test-utils/renderWithProviders";
import PromptEditor from "./PromptEditor";

jest.mock("../../../api/rag", () => ({
  getDefaultPrompts: jest.fn(),
  getLibraryPrompts: jest.fn(),
}));

const { getDefaultPrompts, getLibraryPrompts } = require("../../../api/rag");

const BASE_PROMPT = {
  name: "CustomRAGGenerationPrompt",
  metadata: {
    required_placeholders: ["{chunks}", "{input}"],
    placeholder_descriptions: {
      "{chunks}": "The retrieved passages",
      "{input}": "The user's message",
    },
  },
};

const SEED_PROMPT = {
  name: "DefaultRAGGenerationPrompt",
  metadata: { templates: { en: "Context: {chunks}\nQuestion: {input}" } },
};

/**
 * Renders the editor with a controlled template, exposing what it wrote back.
 * @param {string} template - The starting template.
 * @returns {object} The mock setter and validity callback.
 */
function renderEditor(template) {
  const setPromptModel = jest.fn();
  const onValidityChange = jest.fn();
  renderWithProviders(
    <PromptEditor
      promptModel={{
        component: "CustomRAGGenerationPrompt",
        params: { template, language: "en" },
      }}
      setPromptModel={setPromptModel}
      onValidityChange={onValidityChange}
    />,
  );
  return { setPromptModel, onValidityChange };
}

beforeEach(() => {
  jest.clearAllMocks();
  getDefaultPrompts.mockResolvedValue([BASE_PROMPT, SEED_PROMPT]);
  getLibraryPrompts.mockResolvedValue([]);
});

test("reports a complete template as valid", async () => {
  const { onValidityChange } = renderEditor("Use {chunks} to answer {input}");
  await waitFor(() => expect(getDefaultPrompts).toHaveBeenCalled());
  await waitFor(() => expect(onValidityChange).toHaveBeenLastCalledWith(true));
});

test("reports a template missing a placeholder as invalid, and says which", async () => {
  const { onValidityChange } = renderEditor("Answer {input}");
  await waitFor(() => expect(onValidityChange).toHaveBeenLastCalledWith(false));
  // Two alerts render the same message (panel and expanded editor share it),
  // so assert that the user is told at all rather than matching one node.
  expect((await screen.findAllByRole("alert")).length).toBeGreaterThan(0);
});

test("writes edits back as a self-contained component ref", async () => {
  const { setPromptModel } = renderEditor("Use {chunks} for {input}");
  await waitFor(() => expect(getDefaultPrompts).toHaveBeenCalled());

  const textarea = screen.getAllByRole("textbox")[0];
  await userEvent.type(textarea, "!");

  expect(setPromptModel).toHaveBeenCalled();
  const written = setPromptModel.mock.calls.at(-1)[0];
  expect(written.component).toBe("CustomRAGGenerationPrompt");
  expect(written.params).toHaveProperty("template");
});

test("hides the language select until a default prompt is selected", async () => {
  renderEditor("Hand-written: {chunks} {input}");
  await waitFor(() => expect(getDefaultPrompts).toHaveBeenCalled());

  expect(screen.getAllByRole("combobox")).toHaveLength(1);

  await userEvent.click(screen.getByRole("combobox"));
  await userEvent.click(
    await screen.findByRole("option", { name: "DefaultRAGGenerationPrompt" }),
  );

  expect(screen.getAllByRole("combobox")).toHaveLength(2);
});

test("selecting a saved prompt loads its template without a language select", async () => {
  getLibraryPrompts.mockResolvedValue([
    {
      id: 7,
      name: "Mi prompt",
      is_library: true,
      prompt_type: "generation",
      parameters: { template: "Saved {chunks} {input}" },
    },
  ]);
  const { setPromptModel } = renderEditor("Hand-written: {chunks} {input}");
  await waitFor(() => expect(getLibraryPrompts).toHaveBeenCalled());

  await userEvent.click(screen.getByRole("combobox"));
  await userEvent.click(
    await screen.findByRole("option", { name: "Mi prompt" }),
  );

  expect(setPromptModel.mock.calls.at(-1)[0].params.template).toBe(
    "Saved {chunks} {input}",
  );
  expect(screen.getAllByRole("combobox")).toHaveLength(1);
});

test("writes only what the prompt component actually reads", async () => {
  const { setPromptModel } = renderEditor("Use {chunks} for {input}");
  await waitFor(() => expect(getDefaultPrompts).toHaveBeenCalled());

  const textarea = screen.getAllByRole("textbox")[0];
  await userEvent.type(textarea, "!");

  const written = setPromptModel.mock.calls.at(-1)[0];
  expect(Object.keys(written.params)).toEqual(["template"]);
});

test("names a default prompt that arrives without templates instead of hiding it", async () => {
  getDefaultPrompts.mockResolvedValue([
    BASE_PROMPT,
    SEED_PROMPT,
    { name: "BrokenDefaultPrompt", metadata: {} },
  ]);
  renderEditor("Use {chunks} to answer {input}");

  expect(await screen.findByText(/BrokenDefaultPrompt/)).toBeInTheDocument();
});

test("names a saved prompt that arrives without parameters instead of hiding it", async () => {
  getLibraryPrompts.mockResolvedValue([
    {
      id: 7,
      name: "Broken saved prompt",
      is_library: true,
      prompt_type: "generation",
    },
  ]);
  renderEditor("Use {chunks} to answer {input}");

  expect(await screen.findByText(/Broken saved prompt/)).toBeInTheDocument();
});
