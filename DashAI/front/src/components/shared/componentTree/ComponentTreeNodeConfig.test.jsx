import React from "react";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ComponentTreeNodeConfig from "./ComponentTreeNodeConfig";

jest.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key) => key, i18n: { language: "en" } }),
}));
jest.mock("../RAGAdvancedDialog", () => ({
  __esModule: true,
  default: ({ open, actions, children }) =>
    open ? (
      <div>
        {children}
        {actions}
      </div>
    ) : null,
}));
jest.mock("../FormSchemaContainer", () => ({
  __esModule: true,
  default: ({ children }) => <div>{children}</div>,
}));

const OPTIONS = [{ name: "A" }, { name: "B" }, { name: "C" }];
const LABELS = {
  configureNode: "configure",
  selectComponent: "component",
  parameters: "parameters",
  containerNote: "note",
};

const Form = () => <div data-testid="form" />;

const deferred = () => {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
};

const renderConfig = (resolveDefaults) => {
  const onSave = jest.fn();
  render(
    <ComponentTreeNodeConfig
      open
      nodeId="n_1"
      nodeData={{ component: "A", params: { fromA: 1 } }}
      options={OPTIONS}
      getChildrenField={() => null}
      resolveDefaults={resolveDefaults}
      FormComponent={Form}
      labels={LABELS}
      onSave={onSave}
      onClose={jest.fn()}
    />,
  );
  return onSave;
};

const choose = async (name) => {
  await userEvent.click(screen.getByRole("combobox"));
  await userEvent.click(await screen.findByRole("option", { name }));
};

const saveButton = () => screen.getByRole("button", { name: "common:save" });

describe("ComponentTreeNodeConfig defaults loading", () => {
  it("saves the chosen component with its own defaults", async () => {
    const onSave = renderConfig(jest.fn().mockResolvedValue({ fromB: 2 }));

    await choose("B");
    await waitFor(() => expect(saveButton()).toBeEnabled());
    await userEvent.click(saveButton());

    expect(onSave).toHaveBeenCalledWith("n_1", "B", { fromB: 2 });
  });

  it("shows the failure and keeps the previous component and params", async () => {
    const onSave = renderConfig(
      jest.fn().mockRejectedValue(new Error("network down")),
    );

    await choose("B");

    expect(
      await screen.findByText("common:componentTree.loadFailed"),
    ).toBeInTheDocument();
    await waitFor(() => expect(saveButton()).toBeEnabled());
    await userEvent.click(saveButton());

    expect(onSave).toHaveBeenCalledWith("n_1", "A", { fromA: 1 });
  });

  it("ignores a slow response that a newer selection overtook", async () => {
    const slow = deferred();
    const fast = deferred();
    const resolveDefaults = jest
      .fn()
      .mockReturnValueOnce(slow.promise)
      .mockReturnValueOnce(fast.promise);
    const onSave = renderConfig(resolveDefaults);

    await choose("B");
    await choose("C");
    await act(async () => fast.resolve({ fromC: 3 }));
    await waitFor(() => expect(saveButton()).toBeEnabled());
    await act(async () => slow.resolve({ fromB: 2 }));
    await userEvent.click(saveButton());

    expect(onSave).toHaveBeenCalledWith("n_1", "C", { fromC: 3 });
  });

  it("does not restore the old selection when an overtaken request fails", async () => {
    const slow = deferred();
    const fast = deferred();
    const resolveDefaults = jest
      .fn()
      .mockReturnValueOnce(slow.promise)
      .mockReturnValueOnce(fast.promise);
    const onSave = renderConfig(resolveDefaults);

    await choose("B");
    await choose("C");
    await act(async () => fast.resolve({ fromC: 3 }));
    await waitFor(() => expect(saveButton()).toBeEnabled());
    await act(async () => slow.reject(new Error("late failure")));
    await userEvent.click(saveButton());

    expect(
      screen.queryByText("common:componentTree.loadFailed"),
    ).not.toBeInTheDocument();
    expect(onSave).toHaveBeenCalledWith("n_1", "C", { fromC: 3 });
  });
});
