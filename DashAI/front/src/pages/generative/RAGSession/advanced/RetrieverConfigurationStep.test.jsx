import React from "react";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RetrieverConfigurationStep from "./RetrieverConfigurationStep";
import { getRetrievalParadigm } from "../../../../api/rag";
import { resolveRetrieverDefaults } from "./resolveRetrieverDefaults";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key) => key, i18n: { language: "en" } }),
}));
jest.mock("../../../../api/rag", () => ({ getRetrievalParadigm: jest.fn() }));
jest.mock("./resolveRetrieverDefaults", () => ({
  resolveRetrieverDefaults: jest.fn(async () => ({})),
}));
jest.mock("../../../../contexts/schema", () => ({
  FormSchemaProvider: ({ children }) => <div>{children}</div>,
}));
jest.mock(
  "../../../../components/generative/RAG/FormSchemaWithPrompts",
  () => ({
    __esModule: true,
    default: () => <div data-testid="simple-form" />,
  }),
);
jest.mock("./CompositeRetrieverBuilder", () => ({
  __esModule: true,
  default: (props) => {
    global.mockCompositeProps = props;
    return <div data-testid="composite-builder" />;
  },
}));

const childrenField = {
  type: "array",
  items: { type: "object", parent: "BaseRetriever" },
};
const RETRIEVERS = [
  {
    name: "Seq",
    display_name: "Seq",
    schema: { properties: { children: childrenField } },
  },
  { name: "Other", display_name: "Other", schema: { properties: { x: {} } } },
  { name: "Dense", display_name: "Dense", schema: { properties: { y: {} } } },
];

const renderStep = (retrieverModel) => {
  const setRetrieverModel = jest.fn();
  const setNextEnabled = jest.fn();
  const view = render(
    <RetrieverConfigurationStep
      retrieverModel={retrieverModel}
      setRetrieverModel={setRetrieverModel}
      setNextEnabled={setNextEnabled}
    />,
  );
  return { ...view, setRetrieverModel, setNextEnabled };
};

beforeEach(() => {
  getRetrievalParadigm.mockResolvedValue(RETRIEVERS);
  resolveRetrieverDefaults.mockReset();
  resolveRetrieverDefaults.mockResolvedValue({});
});

const deferred = () => {
  let resolve;
  const promise = new Promise((res) => {
    resolve = res;
  });
  return { promise, resolve };
};

const choose = async (name) => {
  await userEvent.click(screen.getByRole("combobox"));
  await userEvent.click(await screen.findByRole("option", { name }));
};

const chooseAgain = async (name) => {
  await userEvent.clear(screen.getByRole("combobox"));
  await userEvent.click(await screen.findByRole("option", { name }));
};

describe("RetrieverConfigurationStep", () => {
  it("enables Next for a stored simple retriever as soon as it loads", async () => {
    const { setNextEnabled } = renderStep({ component: "Dense", params: {} });

    await screen.findByTestId("simple-form");

    expect(setNextEnabled).toHaveBeenCalledWith(true);
  });

  it("keeps Next disabled for a stored composite until its tree reports it is complete", async () => {
    const { setNextEnabled } = renderStep({
      component: "Seq",
      params: { children: [] },
    });

    await screen.findByTestId("composite-builder");
    expect(setNextEnabled).not.toHaveBeenCalledWith(true);

    act(() => global.mockCompositeProps.onValidityChange(true));

    expect(setNextEnabled).toHaveBeenLastCalledWith(true);
  });

  it("stores a root swapped in the tree under its own component name", async () => {
    const { setRetrieverModel, unmount } = renderStep({
      component: "Seq",
      params: { children: [] },
    });
    await screen.findByTestId("composite-builder");

    act(() =>
      global.mockCompositeProps.onChange(
        { component: "Other", params: { x: 1 } },
        {},
      ),
    );
    unmount();

    expect(setRetrieverModel).toHaveBeenLastCalledWith({
      component: "Other",
      params: { x: 1 },
    });
  });

  it("shows the error when the retriever list cannot be loaded", async () => {
    getRetrievalParadigm.mockRejectedValue(new Error("registry down"));

    renderStep(undefined);

    expect(
      await screen.findByText("common:componentTree.loadFailed"),
    ).toBeInTheDocument();
  });

  it("shows the error and keeps the previous selection when a choice fails", async () => {
    const { setRetrieverModel } = renderStep(undefined);
    await screen.findByRole("combobox");
    resolveRetrieverDefaults.mockRejectedValue(new Error("defaults down"));

    await choose("Dense");

    expect(
      await screen.findByText("common:componentTree.loadFailed"),
    ).toBeInTheDocument();
    expect(setRetrieverModel).not.toHaveBeenCalledWith(
      expect.objectContaining({ component: "Dense" }),
    );
  });

  it("keeps the last choice when an earlier one answers later", async () => {
    const slow = deferred();
    resolveRetrieverDefaults
      .mockReturnValueOnce(slow.promise)
      .mockResolvedValueOnce({ fromOther: 1 });
    const { setRetrieverModel } = renderStep(undefined);
    await screen.findByRole("combobox");

    await choose("Dense");
    await chooseAgain("Other");
    await waitFor(() =>
      expect(setRetrieverModel).toHaveBeenCalledWith({
        component: "Other",
        params: { fromOther: 1 },
      }),
    );
    await act(async () => slow.resolve({ fromDense: 1 }));

    expect(setRetrieverModel).not.toHaveBeenCalledWith(
      expect.objectContaining({ component: "Dense" }),
    );
  });

  it("shows the error instead of an empty form when the defaults fail to load", async () => {
    resolveRetrieverDefaults.mockRejectedValue(new Error("defaults down"));

    renderStep({ component: "Dense", params: {} });

    expect(
      await screen.findByText("common:componentTree.loadFailed"),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("simple-form")).not.toBeInTheDocument();
  });

  it("reports a root swapped for an unavailable component", async () => {
    renderStep({ component: "Seq", params: { children: [] } });
    await screen.findByTestId("composite-builder");

    act(() =>
      global.mockCompositeProps.onChange({ component: "Gone", params: {} }, {}),
    );

    expect(
      await screen.findByText("common:componentTree.loadFailed"),
    ).toBeInTheDocument();
  });
});
