import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import ComponentTreeBuilder from "./ComponentTreeBuilder";
import { getChildComponents } from "../../../api/component";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key) => key, i18n: { language: "en" } }),
}));
jest.mock("../../../api/component", () => ({ getChildComponents: jest.fn() }));
jest.mock("../FormSchema", () => ({ __esModule: true, default: () => null }));
jest.mock("./ComponentTreeNodeConfig", () => ({
  __esModule: true,
  default: ({ nodeId, options, onSave, onClose }) => (
    <div data-testid="node-config" data-options={options.map((o) => o.name)}>
      <button type="button" onClick={() => onSave(nodeId, "Leaf", { x: 1 })}>
        save-leaf
      </button>
      <button type="button" onClick={onClose}>
        close-config
      </button>
    </div>
  ),
}));

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

  it("hands the initial tree to onLoad and never reports it as an edit", async () => {
    const onChange = jest.fn();
    const onLoad = jest.fn();
    renderTree({ onChange, onLoad, rootComponent: "Many" });
    await screen.findByText("Many");

    expect(onLoad).toHaveBeenCalledTimes(1);
    expect(onLoad).toHaveBeenCalledWith(
      { component: "Many", params: { kids: [] } },
      { findComponent: expect.any(Function) },
    );
    expect(onChange).not.toHaveBeenCalled();
  });

  it("shows an error instead of a made-up root when the root component is unknown", async () => {
    const onChange = jest.fn();
    const onLoad = jest.fn();
    renderTree({ onChange, onLoad, rootComponent: "Missing" });

    expect(
      await screen.findByText("common:componentTree.unknownComponent"),
    ).toBeInTheDocument();
    expect(onLoad).not.toHaveBeenCalled();
    expect(onChange).not.toHaveBeenCalled();
  });

  it("shows an error for an unknown child and keeps it when the tree is saved", async () => {
    const onChange = jest.fn();
    const onLoad = jest.fn();
    renderTree({
      onChange,
      onLoad,
      rootComponent: "Many",
      rootParams: {
        kids: [
          { component: "Leaf", params: {} },
          { component: "Ghost", params: { a: 1 } },
        ],
      },
    });

    expect(
      await screen.findByText("common:componentTree.unknownChild"),
    ).toBeInTheDocument();
    expect(onLoad).toHaveBeenCalledWith(
      {
        component: "Many",
        params: {
          kids: [
            { component: "Leaf", params: {} },
            { component: "Ghost", params: { a: 1 } },
          ],
        },
      },
      { findComponent: expect.any(Function) },
    );

    fireEvent.click(
      screen.getAllByLabelText("common:componentTree.removeNode")[0],
    );

    expect(onChange).toHaveBeenLastCalledWith(
      {
        component: "Many",
        params: { kids: [{ component: "Ghost", params: { a: 1 } }] },
      },
      expect.any(Object),
    );
  });

  it("loads the parent declared by the container for its children", async () => {
    renderTree({ rootComponent: "Many", rootParams: {} });
    await screen.findByText("Many");

    expect(getChildComponents).toHaveBeenCalledWith("Scorable", true);
  });

  it("opens the configuration of a new child with the parent its container declares", async () => {
    renderTree({ rootComponent: "Many", rootParams: { kids: [] } });

    fireEvent.click(
      await screen.findByLabelText("common:componentTree.addChild"),
    );

    const config = await screen.findByTestId("node-config");
    expect(config).toHaveAttribute("data-options", "Single,Many,Leaf");
  });

  it("offers the root's parent components when the root is edited", async () => {
    getChildComponents.mockImplementation(async (parent) =>
      parent === "Root" ? [CATALOG.Scorable[0]] : (CATALOG[parent] ?? []),
    );
    renderTree({ parent: "Root", rootComponent: "Single", rootParams: {} });

    fireEvent.click(
      await screen.findByLabelText(/common:componentTree.configureNode/),
    );

    expect(await screen.findByTestId("node-config")).toHaveAttribute(
      "data-options",
      "Single",
    );
  });

  it("reports the saved child when its configuration is saved", async () => {
    const onChange = jest.fn();
    renderTree({ onChange, rootComponent: "Many", rootParams: { kids: [] } });
    fireEvent.click(
      await screen.findByLabelText("common:componentTree.addChild"),
    );

    fireEvent.click(await screen.findByText("save-leaf"));

    await waitFor(() =>
      expect(onChange).toHaveBeenLastCalledWith(
        {
          component: "Many",
          params: { kids: [{ component: "Leaf", params: { x: 1 } }] },
        },
        { findComponent: expect.any(Function) },
      ),
    );
    expect(screen.queryByTestId("node-config")).not.toBeInTheDocument();
  });

  it("drops the placeholder child when the configuration is cancelled", async () => {
    const onChange = jest.fn();
    renderTree({ onChange, rootComponent: "Many", rootParams: { kids: [] } });
    fireEvent.click(
      await screen.findByLabelText("common:componentTree.addChild"),
    );

    fireEvent.click(await screen.findByText("close-config"));

    await waitFor(() =>
      expect(onChange).toHaveBeenLastCalledWith(
        { component: "Many", params: { kids: [] } },
        { findComponent: expect.any(Function) },
      ),
    );
    expect(screen.queryByTestId("node-config")).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText("common:componentTree.removeNode"),
    ).not.toBeInTheDocument();
  });

  it("shows why the registry failed to load and never reports a tree", async () => {
    const onChange = jest.fn();
    getChildComponents.mockRejectedValue(new Error("registry down"));
    const onLoad = jest.fn();
    renderTree({ onChange, onLoad, rootComponent: "Many" });

    expect(
      await screen.findByText("common:componentTree.loadFailed"),
    ).toBeInTheDocument();
    expect(onChange).not.toHaveBeenCalled();
    expect(onLoad).not.toHaveBeenCalled();
    expect(screen.queryByText("Many")).not.toBeInTheDocument();
  });
});
