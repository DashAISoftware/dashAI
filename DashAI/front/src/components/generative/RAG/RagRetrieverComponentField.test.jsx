import React from "react";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RagRetrieverComponentField, {
  retrieverFieldInfo,
} from "./RagRetrieverComponentField";
import useModelParents from "../../../hooks/useModelParents";
import useSchema from "../../../hooks/useSchema";
import {
  formattedModel,
  generateYupSchema,
  getModelFromSubform,
} from "../../../utils/schema";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key) => key }),
  initReactI18next: { type: "3rdParty", init: () => {} },
}));
jest.mock("../../../hooks/useModelParents", () => ({
  __esModule: true,
  default: jest.fn(),
}));
jest.mock("../../../hooks/useSchema", () => ({
  __esModule: true,
  default: jest.fn(),
}));
jest.mock("../../../utils/schema", () => ({
  ...jest.requireActual("../../../utils/schema"),
  formattedModel: jest.fn(),
  generateYupSchema: jest.fn(),
}));
jest.mock("../../shared/FormSchema", () => ({
  __esModule: true,
  default: ({ formSubmitRef, onFormSubmit }) => {
    if (formSubmitRef) {
      formSubmitRef.current = global.mockFormik
        ? {
            values: global.mockFormik.values,
            validateForm: async () => global.mockFormik.errors,
            submitForm: async () => {
              if (Object.keys(global.mockFormik.errors).length === 0) {
                onFormSubmit(global.mockFormik.values);
              }
            },
          }
        : null;
    }
    return null;
  },
}));
jest.mock("../../shared/FormSchemaContainer", () => ({
  __esModule: true,
  default: ({ children }) => <div>{children}</div>,
}));
jest.mock(
  "../../../pages/generative/RAGSession/advanced/CompositeRetrieverBuilder",
  () => ({
    __esModule: true,
    default: ({ rootComponent, rootParent, rootParams }) => (
      <div
        data-testid="tree"
        data-root={rootComponent}
        data-parent={rootParent}
        data-params={JSON.stringify(rootParams)}
      />
    ),
  }),
);

const childrenSchema = {
  properties: {
    children: {
      type: "array",
      items: { type: "object", parent: "BaseRetriever" },
    },
  },
};

const MODELS = [
  { name: "Dense", display_name: "Dense", schema: { properties: {} } },
  { name: "MMR", display_name: "MMR", schema: childrenSchema },
  { name: "Bare", display_name: "Bare" },
];

const renderField = (props = {}) => {
  const onChange = jest.fn();
  const onValidityChange = jest.fn();
  render(
    <RagRetrieverComponentField
      name="reranker"
      parent="ChunkScorer"
      label="Reranker"
      field={{ value: undefined, onChange }}
      onValidityChange={onValidityChange}
      {...props}
    />,
  );
  return { onChange, onValidityChange };
};

beforeEach(() => {
  global.mockFormik = {
    values: { top_k: 7 },
    errors: {},
  };
  useModelParents.mockReturnValue({ models: MODELS, error: null });
  useSchema.mockReturnValue({
    modelSchema: { properties: {} },
    defaultValues: { children: [] },
  });
});

describe("retrieverFieldInfo", () => {
  it("recognises a plain and a nullable retriever component field", () => {
    expect(
      retrieverFieldInfo({ type: "object", parent: "ChunkScorer" }),
    ).toEqual({ parent: "ChunkScorer", nullable: false });
    expect(
      retrieverFieldInfo({
        anyOf: [{ type: "object", parent: "ChunkScorer" }, { type: "null" }],
      }),
    ).toEqual({ parent: "ChunkScorer", nullable: true });
  });

  it("ignores a union that mixes in other types", () => {
    expect(
      retrieverFieldInfo({
        anyOf: [{ type: "object", parent: "ChunkScorer" }, { type: "integer" }],
      }),
    ).toBeNull();
  });
});

describe("RagRetrieverComponentField", () => {
  it("roots the tree of a composite in the field's own parent", () => {
    renderField({
      field: {
        value: { component: "MMR", params: { children: [] } },
        onChange: jest.fn(),
      },
    });

    const tree = screen.getByTestId("tree");
    expect(tree).toHaveAttribute("data-root", "MMR");
    expect(tree).toHaveAttribute("data-parent", "ChunkScorer");
    expect(tree).toHaveAttribute("data-params", '{"children":[]}');
  });

  it("does not mount the tree before the defaults of an unset composite load", () => {
    useSchema.mockReturnValue({ modelSchema: null, defaultValues: {} });
    renderField({
      field: { value: { component: "MMR" }, onChange: jest.fn() },
    });

    expect(screen.queryByTestId("tree")).not.toBeInTheDocument();
  });

  it("reports the field invalid while the component list is still unloaded", () => {
    useModelParents.mockReturnValue({ models: null, error: null });
    const { onValidityChange } = renderField({
      field: {
        value: { component: "MMR", params: { children: [] } },
        onChange: jest.fn(),
      },
    });

    expect(onValidityChange).toHaveBeenLastCalledWith(false);
  });

  it("keeps the field invalid and says so when the component list fails to load", () => {
    useModelParents.mockReturnValue({
      models: null,
      error: new Error("offline"),
    });
    const { onValidityChange } = renderField({
      field: {
        value: { component: "MMR", params: { children: [] } },
        onChange: jest.fn(),
      },
    });

    expect(onValidityChange).toHaveBeenLastCalledWith(false);
    expect(
      screen.getByText("common:componentTree.loadFailed"),
    ).toBeInTheDocument();
  });

  it("reports a plain component valid once the list is loaded", () => {
    const { onValidityChange } = renderField({
      field: {
        value: { component: "Dense", params: {} },
        onChange: jest.fn(),
      },
    });

    expect(onValidityChange).toHaveBeenLastCalledWith(true);
  });

  it("shows the selector for an unset non-nullable field instead of Null", () => {
    renderField({ nullable: false });

    expect(screen.getByRole("combobox")).toBeInTheDocument();
    expect(screen.queryByText("common:null")).not.toBeInTheDocument();
  });

  it("shows the selector, not Null, for an unset nullable field", () => {
    renderField({ nullable: true });

    expect(screen.getByRole("combobox")).toBeInTheDocument();
    expect(screen.getByText("common:null")).toBeInTheDocument();
  });

  it("treats only an explicit null as Null", () => {
    renderField({
      nullable: true,
      field: { value: null, onChange: jest.fn() },
    });

    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("turns a component off with Null and restores the placeholder with Component", async () => {
    const onChange = jest.fn();
    const placeholder = { component: "Dense", params: { top_k: 3 } };
    const { rerender } = render(
      <RagRetrieverComponentField
        name="reranker"
        parent="ChunkScorer"
        label="Reranker"
        nullable
        placeholder={placeholder}
        field={{ value: placeholder, onChange }}
      />,
    );

    await userEvent.click(screen.getByText("common:null"));
    expect(onChange).toHaveBeenLastCalledWith(null);

    rerender(
      <RagRetrieverComponentField
        name="reranker"
        parent="ChunkScorer"
        label="Reranker"
        nullable
        placeholder={placeholder}
        field={{ value: null, onChange }}
      />,
    );
    await userEvent.click(screen.getByText("common:component"));
    expect(onChange).toHaveBeenLastCalledWith(placeholder);
  });

  it("reports the field valid again when it unmounts", () => {
    const onValidityChange = jest.fn();
    const { unmount } = render(
      <RagRetrieverComponentField
        name="reranker"
        parent="ChunkScorer"
        label="Reranker"
        field={{
          value: { component: "MMR", params: { children: [] } },
          onChange: jest.fn(),
        }}
        onValidityChange={onValidityChange}
      />,
    );
    onValidityChange.mockClear();

    unmount();

    expect(onValidityChange).toHaveBeenCalledWith(true);
  });

  it("reports a stored composite invalid while its params are still loading", () => {
    useSchema.mockReturnValue({ modelSchema: null, defaultValues: {} });
    const { onValidityChange } = renderField({
      field: { value: { component: "MMR" }, onChange: jest.fn() },
    });

    expect(onValidityChange).toHaveBeenLastCalledWith(false);
  });

  it("says so when a model without a configuration schema is chosen", async () => {
    const { onChange } = renderField();

    await userEvent.click(screen.getByRole("combobox"));
    await userEvent.click(screen.getByRole("option", { name: "Bare" }));

    expect(
      await screen.findByText("common:componentTree.loadFailed"),
    ).toBeInTheDocument();
    expect(onChange).not.toHaveBeenCalled();
  });

  it("keeps the last selection when an earlier one resolves after it", async () => {
    const resolvers = {};
    formattedModel.mockImplementation(
      (schema) =>
        new Promise((resolve) => {
          resolvers[schema === MODELS[0].schema ? "Dense" : "MMR"] = () =>
            resolve(schema);
        }),
    );
    generateYupSchema.mockImplementation((schema) => ({
      initialValues: { from: schema === MODELS[0].schema ? "Dense" : "MMR" },
    }));
    const { onChange } = renderField();

    await userEvent.click(screen.getByRole("combobox"));
    await userEvent.click(screen.getByRole("option", { name: "Dense" }));
    await userEvent.click(screen.getByRole("combobox"));
    await userEvent.click(screen.getByRole("option", { name: "MMR" }));

    await act(async () => {
      resolvers.MMR();
      await Promise.resolve();
    });
    await act(async () => {
      resolvers.Dense();
      await Promise.resolve();
    });

    await waitFor(() => expect(onChange).toHaveBeenCalledTimes(1));
    expect(getModelFromSubform(onChange.mock.calls[0][0])).toBe("MMR");
  });

  it("shows why a selection failed instead of an unhandled rejection", async () => {
    formattedModel.mockRejectedValue(new Error("bad schema"));
    renderField();

    await userEvent.click(screen.getByRole("combobox"));
    await userEvent.click(screen.getByRole("option", { name: "Dense" }));

    expect(
      await screen.findByText("common:componentTree.loadFailed"),
    ).toBeInTheDocument();
  });

  describe("settings dialog", () => {
    const openDialog = async (onChange = jest.fn()) => {
      renderField({
        field: { value: { component: "Dense", params: {} }, onChange },
      });
      await userEvent.click(
        screen.getByRole("button", { name: "common:configureSubmodel" }),
      );
      return onChange;
    };
    const save = () =>
      userEvent.click(screen.getByRole("button", { name: "common:save" }));

    it("stores the submitted values and closes", async () => {
      const onChange = await openDialog();

      await save();

      await waitFor(() => expect(onChange).toHaveBeenCalledTimes(1));
      expect(getModelFromSubform(onChange.mock.calls[0][0])).toBe("Dense");
      await waitFor(() =>
        expect(
          screen.queryByRole("button", { name: "common:save" }),
        ).not.toBeInTheDocument(),
      );
    });

    it("keeps the dialog open and stores nothing while the values are invalid", async () => {
      global.mockFormik.errors = { top_k: "required" };
      const onChange = await openDialog();

      await save();

      expect(onChange).not.toHaveBeenCalled();
      expect(
        screen.getByRole("button", { name: "common:save" }),
      ).toBeInTheDocument();
    });

    it("says the form is not ready instead of saving other values", async () => {
      global.mockFormik = null;
      const onChange = await openDialog();

      await save();

      expect(
        await screen.findByText("common:componentTree.formUnavailable"),
      ).toBeInTheDocument();
      expect(onChange).not.toHaveBeenCalled();
    });
  });
});
