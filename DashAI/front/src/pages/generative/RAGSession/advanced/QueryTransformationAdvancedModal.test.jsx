import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import QueryTransformationAdvancedModal from "./QueryTransformationAdvancedModal";
import { resolveRagLlmDefaults } from "./resolveRagLlmDefaults";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key) => key }),
}));
jest.mock("../../../../components/shared/RAGAdvancedDialog", () => ({
  __esModule: true,
  default: ({ open, title, actions, children }) =>
    open ? (
      <div>
        <h2>{title}</h2>
        {children}
        {actions}
      </div>
    ) : null,
}));
jest.mock("./resolveRagLlmDefaults", () => ({
  resolveRagLlmDefaults: jest.fn(),
}));
jest.mock("../../../../components/shared/FormSchema", () => ({
  __esModule: true,
  default: () => null,
}));
jest.mock("../../../../components/shared/FormSchemaContainer", () => ({
  __esModule: true,
  default: ({ children }) => <div>{children}</div>,
}));
jest.mock(
  "../../../../components/generative/RAG/FormSchemaWithPrompts",
  () => ({
    __esModule: true,
    default: ({ onRetrieversCompleteChange }) => (
      <div>
        <button type="button" onClick={() => onRetrieversCompleteChange(false)}>
          make-composite-incomplete
        </button>
        <button type="button" onClick={() => onRetrieversCompleteChange(true)}>
          make-composite-complete
        </button>
      </div>
    ),
  }),
);

beforeEach(() => {
  resolveRagLlmDefaults.mockResolvedValue({});
});

const GENERATORS = [
  { name: "Downloaded", downloaded: true, display_name: "Downloaded model" },
  { name: "Missing", downloaded: false, display_name: "Missing model" },
];

const modelWith = (llm) => ({
  component: "LLMQueryExpander",
  params: {
    llm_model: { component: llm, params: {} },
    prompt: { component: "Prompt", params: {} },
  },
});

const renderModal = (model, setModel = jest.fn()) => {
  render(
    <QueryTransformationAdvancedModal
      open
      onClose={jest.fn()}
      model={model}
      setModel={setModel}
      technique="expansion"
      generators={GENERATORS}
    />,
  );
  return setModel;
};

const doneButton = () =>
  screen.getByRole("button", { name: "generative:rag.advanced.done" });

describe("QueryTransformationAdvancedModal completeness", () => {
  it("allows saving a complete stage with a downloaded model", async () => {
    const setModel = renderModal(modelWith("Downloaded"));

    expect(doneButton()).toBeEnabled();
    await userEvent.click(doneButton());

    expect(setModel).toHaveBeenCalledTimes(1);
  });

  it("blocks saving when the chosen model is not downloaded", () => {
    const setModel = renderModal(modelWith("Missing"));

    expect(doneButton()).toBeDisabled();
    expect(
      screen.getByText(
        "generative:rag.config.queryTransformation.needsDownloadedModel",
      ),
    ).toBeInTheDocument();
    expect(setModel).not.toHaveBeenCalled();
  });

  it("asks for a prompt and a model when the ref is incomplete", () => {
    renderModal({ component: "LLMQueryExpander", params: {} });

    expect(doneButton()).toBeDisabled();
    expect(
      screen.getByText("generative:rag.config.queryTransformation.incomplete"),
    ).toBeInTheDocument();
  });

  it("explains an incomplete composite reranker with its own message", async () => {
    renderModal(modelWith("Downloaded"));

    await userEvent.click(
      screen.getByRole("button", { name: "make-composite-incomplete" }),
    );

    expect(doneButton()).toBeDisabled();
    expect(
      screen.getByText(
        "generative:rag.config.queryTransformation.compositeIncomplete",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(
        "generative:rag.config.queryTransformation.incomplete",
      ),
    ).not.toBeInTheDocument();

    await userEvent.click(
      screen.getByRole("button", { name: "make-composite-complete" }),
    );
    expect(doneButton()).toBeEnabled();
  });

  it("shows an error and blocks saving when the model defaults fail to load", async () => {
    resolveRagLlmDefaults.mockRejectedValue(new Error("network down"));
    const setModel = renderModal(modelWith("Downloaded"));

    expect(
      await screen.findByText(
        "generative:rag.config.queryTransformation.loadFailed",
      ),
    ).toBeInTheDocument();
    expect(doneButton()).toBeDisabled();
    expect(setModel).not.toHaveBeenCalled();
  });
});
