import React from "react";
import { render, screen } from "@testing-library/react";
import CompositeRetrieverBuilder from "./CompositeRetrieverBuilder";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key) => key, i18n: { language: "en" } }),
}));
jest.mock("@mui/material/styles", () => ({
  ...jest.requireActual("@mui/material/styles"),
  useTheme: () => ({ palette: { divider: "#ccc" } }),
}));
jest.mock(
  "../../../../components/shared/componentTree/ComponentTreeBuilder",
  () => ({
    __esModule: true,
    default: (props) => {
      global.mockBuilderProps = props;
      return <div data-testid="builder" data-parent={props.parent}></div>;
    },
  }),
);
jest.mock(
  "../../../../components/generative/RAG/FormSchemaWithPrompts",
  () => ({
    __esModule: true,
    default: () => null,
  }),
);
jest.mock("./resolveRetrieverDefaults", () => ({
  resolveRetrieverDefaults: jest.fn(),
}));

const SCHEMAS = {
  Seq: {
    schema: {
      properties: {
        children: {
          type: "array",
          items: { type: "object", parent: "BaseRetriever" },
        },
      },
    },
  },
  Dense: { schema: { properties: {} } },
};
const findComponent = (name) => SCHEMAS[name] ?? null;

describe("CompositeRetrieverBuilder", () => {
  it("roots the tree in every retriever by default", () => {
    render(
      <CompositeRetrieverBuilder
        rootComponent="Seq"
        rootParams={{}}
        onChange={jest.fn()}
      />,
    );

    expect(screen.getByTestId("builder")).toHaveAttribute(
      "data-parent",
      "BaseRetriever",
    );
  });

  it("roots the tree in the parent the field restricts it to", () => {
    render(
      <CompositeRetrieverBuilder
        rootComponent="Seq"
        rootParams={{}}
        rootParent="ChunkScorer"
        onChange={jest.fn()}
      />,
    );

    expect(screen.getByTestId("builder")).toHaveAttribute(
      "data-parent",
      "ChunkScorer",
    );
  });

  it("reports validity on load without writing the tree back", () => {
    const onChange = jest.fn();
    const onValidityChange = jest.fn();
    render(
      <CompositeRetrieverBuilder
        rootComponent="Seq"
        rootParams={{}}
        onChange={onChange}
        onValidityChange={onValidityChange}
      />,
    );
    const { onLoad } = global.mockBuilderProps;

    onLoad({ component: "Seq", params: { children: [] } }, { findComponent });

    expect(onValidityChange).toHaveBeenLastCalledWith(false);
    expect(onChange).not.toHaveBeenCalled();
  });

  it("reports the tree and whether every composite in it has children", () => {
    const onChange = jest.fn();
    const onValidityChange = jest.fn();
    render(
      <CompositeRetrieverBuilder
        rootComponent="Seq"
        rootParams={{}}
        onChange={onChange}
        onValidityChange={onValidityChange}
      />,
    );
    const { onChange: handleTreeChange } = global.mockBuilderProps;

    handleTreeChange(
      { component: "Seq", params: { children: [] } },
      { findComponent },
    );
    expect(onValidityChange).toHaveBeenLastCalledWith(false);

    handleTreeChange(
      {
        component: "Seq",
        params: { children: [{ component: "Dense", params: {} }] },
      },
      { findComponent },
    );
    expect(onValidityChange).toHaveBeenLastCalledWith(true);
    expect(onChange).toHaveBeenCalledTimes(2);
  });
});
