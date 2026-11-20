import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import ComponentTreeBuilder from "./ComponentTreeBuilder";
import { getChildComponents } from "../../../api/component";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key) => key, i18n: { language: "en" } }),
}));
jest.mock("../../../api/component", () => ({ getChildComponents: jest.fn() }));
// The params form is covered by its own tests; the tree only needs a stand-in.
jest.mock("../FormSchema", () => ({ __esModule: true, default: () => null }));

const listOf = (parent, extra = {}) => ({
  type: "array",
  items: { parent, type: "object" },
  ...extra,
});

const CATALOG = {
  Scorable: [
    {
      name: "Single",
      display_name: "Single",
      schema: {
        properties: { kids: listOf("Scorable", { minItems: 1, maxItems: 1 }) },
      },
    },
    {
      name: "Many",
      display_name: "Many",
      schema: { properties: { kids: listOf("Scorable") } },
    },
    { name: "Leaf", display_name: "Leaf", schema: { properties: {} } },
  ],
};

beforeEach(() => {
  getChildComponents.mockImplementation(
    async (parent) => CATALOG[parent] ?? [],
  );
});

const renderTree = (props) =>
  render(
    <ComponentTreeBuilder parent="Scorable" onChange={jest.fn()} {...props} />,
  );

describe("ComponentTreeBuilder", () => {
  it("shows the root and its children, read from the declared children field", async () => {
    renderTree({
      rootComponent: "Many",
      rootParams: { kids: [{ component: "Leaf", params: {} }] },
    });

    expect(await screen.findByText("Many")).toBeInTheDocument();
    expect(screen.getByText("Leaf")).toBeInTheDocument();
  });

  it("offers adding a child while the declared maxItems allows it", async () => {
    renderTree({ rootComponent: "Many", rootParams: { kids: [] } });

    expect(
      await screen.findByLabelText("common:componentTree.addChild"),
    ).toBeInTheDocument();
  });

  it("hides adding a child once the declared maxItems is reached", async () => {
    renderTree({
      rootComponent: "Single",
      rootParams: { kids: [{ component: "Leaf", params: {} }] },
    });

    await screen.findByText("Single");
    expect(
      screen.queryByLabelText("common:componentTree.addChild"),
    ).not.toBeInTheDocument();
  });

  it("reports the serialised tree when a child is removed", async () => {
    const onChange = jest.fn();
    renderTree({
      onChange,
      rootComponent: "Many",
      rootParams: { kids: [{ component: "Leaf", params: {} }] },
    });
    await screen.findByText("Leaf");

    fireEvent.click(screen.getByLabelText("common:componentTree.removeNode"));

    await waitFor(() =>
      expect(onChange).toHaveBeenCalledWith(
        { component: "Many", params: { kids: [] } },
        { findComponent: expect.any(Function) },
      ),
    );
  });

  it("reports the initial tree only when emitOnLoad is set", async () => {
    const onChange = jest.fn();
    renderTree({ onChange, emitOnLoad: true, rootComponent: "Many" });
    await screen.findByText("Many");

    expect(onChange).toHaveBeenCalledWith(
      { component: "Many", params: { kids: [] } },
      { findComponent: expect.any(Function) },
    );
  });

  it("loads the parent declared by the container for its children", async () => {
    renderTree({ rootComponent: "Many", rootParams: {} });
    await screen.findByText("Many");

    expect(getChildComponents).toHaveBeenCalledWith("Scorable", true);
  });
});
