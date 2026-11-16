import React from "react";
import { fireEvent, screen, within } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import ExportMetadataPanel from "./ExportMetadataPanel";

// See FormSchemaRenderFields.test.jsx: react-markdown is ESM only.
jest.mock("react-markdown", () => ({
  __esModule: true,
  default: ({ children }) => <span>{children}</span>,
}));

// The schema form fetches its schema from the backend; a stub stands in for
// it and exposes a fake formik object through formSubmitRef, as the real
// form does once its schema has loaded.
const mockFormik = { values: {}, setFieldValue: jest.fn() };
const mockFormSchemaProps = jest.fn();
jest.mock("../shared/FormSchema", () => (props) => {
  mockFormSchemaProps(props);
  props.formSubmitRef.current = mockFormik;
  return null;
});
jest.mock(
  "../shared/FormSchemaContainer",
  () =>
    ({ children }) =>
      children,
);

// Field names are made up on purpose: the panel must work from the schema
// marks alone, whatever the platform calls its column fields.
const LABEL = {
  key: "label_column",
  title: "Label column",
  description: "Column to predict.",
  multiple: false,
  required: true,
};
const SKIPPED = {
  key: "skipped_columns",
  title: "Skipped columns",
  description: "Columns left as metadata.",
  multiple: true,
  required: false,
};

const renderPanel = (props = {}) => {
  const handlers = {
    onColumnChange: jest.fn(),
    onValuesChange: jest.fn(),
    setError: jest.fn(),
  };
  renderWithProviders(
    <ExportMetadataPanel
      exporterName="SomeExporter"
      columnFields={[LABEL, SKIPPED]}
      columns={["id", "price", "category"]}
      columnValues={{}}
      initialValues={{ name: "catalog" }}
      formSubmitRef={{ current: null }}
      {...handlers}
      {...props}
    />,
  );
  return handlers;
};

const openSelect = (name) => {
  fireEvent.mouseDown(screen.getByRole("combobox", { name }));
  return within(screen.getByRole("listbox"));
};

describe("ExportMetadataPanel", () => {
  beforeEach(() => {
    mockFormik.values = { label_column: "", skipped_columns: null };
    mockFormik.setFieldValue.mockClear();
    mockFormSchemaProps.mockClear();
  });

  it("draws one selector per column field, titled as the schema says", () => {
    renderPanel();

    expect(screen.getByText("Label column")).toBeInTheDocument();
    expect(screen.getByText("Columns left as metadata.")).toBeInTheDocument();
    expect(
      screen.getByRole("combobox", { name: "Skipped columns" }),
    ).toBeInTheDocument();
  });

  it("draws no selector when the platform declares no column field", () => {
    renderPanel({ columnFields: [] });

    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(mockFormSchemaProps).toHaveBeenCalledWith(
      expect.objectContaining({ excludeFields: [] }),
    );
  });

  it("offers the dataset columns in a single column field", () => {
    const { onColumnChange } = renderPanel();

    fireEvent.click(
      openSelect("Label column").getByRole("option", { name: "category" }),
    );

    expect(onColumnChange).toHaveBeenCalledWith("label_column", "category");
  });

  it("does not offer a column already picked in a single field", () => {
    renderPanel({ columnValues: { label_column: "category" } });

    const options = openSelect("Skipped columns").getAllByRole("option");

    expect(options.map((option) => option.textContent)).toEqual([
      "id",
      "price",
    ]);
  });

  it("frees a column from the multiple fields when a single field takes it", () => {
    const { onColumnChange } = renderPanel({
      columnValues: { skipped_columns: ["id", "price"] },
    });

    fireEvent.click(
      openSelect("Label column").getByRole("option", { name: "price" }),
    );

    expect(onColumnChange).toHaveBeenCalledWith("label_column", "price");
    expect(onColumnChange).toHaveBeenCalledWith("skipped_columns", ["id"]);
  });

  it("hands the column fields to the form instead of drawing them twice", () => {
    renderPanel();

    expect(mockFormSchemaProps).toHaveBeenCalledWith(
      expect.objectContaining({
        model: "SomeExporter",
        excludeFields: ["label_column", "skipped_columns"],
        initialValues: { name: "catalog" },
      }),
    );
  });

  it("mirrors the picked columns into the form values", () => {
    renderPanel({
      columnValues: { label_column: "category", skipped_columns: ["id"] },
    });

    expect(mockFormik.setFieldValue).toHaveBeenCalledWith(
      "label_column",
      "category",
    );
    expect(mockFormik.setFieldValue).toHaveBeenCalledWith("skipped_columns", [
      "id",
    ]);
  });

  it("waits for the form schema before mirroring the columns", () => {
    mockFormik.values = {};
    renderPanel({ columnValues: { label_column: "category" } });

    expect(mockFormik.setFieldValue).not.toHaveBeenCalled();
  });
});
