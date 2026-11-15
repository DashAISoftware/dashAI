import React from "react";
import { fireEvent, screen, within } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import ExportMetadataPanel, {
  IGNORED_FIELD,
  TARGET_FIELD,
} from "./ExportMetadataPanel";

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

const renderPanel = (props = {}) => {
  const handlers = {
    onTargetChange: jest.fn(),
    onIgnoredChange: jest.fn(),
    onValuesChange: jest.fn(),
    setError: jest.fn(),
  };
  renderWithProviders(
    <ExportMetadataPanel
      exporterName="OpenMLDatasetExporter"
      columns={["id", "price", "category"]}
      target=""
      ignored={[]}
      initialValues={{ name: "catalog" }}
      formSubmitRef={{ current: null }}
      {...handlers}
      {...props}
    />,
  );
  return handlers;
};

const openSelect = (index) => {
  fireEvent.mouseDown(screen.getAllByRole("combobox")[index]);
  return within(screen.getByRole("listbox"));
};

describe("ExportMetadataPanel", () => {
  beforeEach(() => {
    mockFormik.values = { [TARGET_FIELD]: "", [IGNORED_FIELD]: null };
    mockFormik.setFieldValue.mockClear();
    mockFormSchemaProps.mockClear();
  });

  it("offers the dataset columns as target", () => {
    const { onTargetChange } = renderPanel();

    fireEvent.click(openSelect(0).getByRole("option", { name: "category" }));

    expect(onTargetChange).toHaveBeenCalledWith("category");
  });

  it("does not offer the target as an ignored column", () => {
    renderPanel({ target: "category" });

    const options = openSelect(1).getAllByRole("option");

    expect(options.map((option) => option.textContent)).toEqual([
      "id",
      "price",
    ]);
  });

  it("drops a column from the ignored ones when it becomes the target", () => {
    const { onIgnoredChange } = renderPanel({ ignored: ["id", "price"] });

    fireEvent.click(openSelect(0).getByRole("option", { name: "price" }));

    expect(onIgnoredChange).toHaveBeenCalledWith(["id"]);
  });

  it("hands the column fields to the form instead of drawing them twice", () => {
    renderPanel();

    expect(mockFormSchemaProps).toHaveBeenCalledWith(
      expect.objectContaining({
        model: "OpenMLDatasetExporter",
        excludeFields: [TARGET_FIELD, IGNORED_FIELD],
        initialValues: { name: "catalog" },
      }),
    );
  });

  it("mirrors the selected columns into the form values", () => {
    renderPanel({ target: "category", ignored: ["id"] });

    expect(mockFormik.setFieldValue).toHaveBeenCalledWith(
      TARGET_FIELD,
      "category",
    );
    expect(mockFormik.setFieldValue).toHaveBeenCalledWith(IGNORED_FIELD, [
      "id",
    ]);
  });

  it("waits for the form schema before mirroring the columns", () => {
    mockFormik.values = {};
    renderPanel({ target: "category" });

    expect(mockFormik.setFieldValue).not.toHaveBeenCalled();
  });
});
