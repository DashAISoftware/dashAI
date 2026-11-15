import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import { TextMessage } from "./TextMessage";

// The highlighter and its styles ship ESM that CRA's Jest does not transform,
// and the colors are not under test: what matters is which component renders.
jest.mock("react-syntax-highlighter", () => ({
  Prism: ({ children }) => <pre>{children}</pre>,
}));
jest.mock("react-syntax-highlighter/dist/esm/styles/prism", () => ({
  oneDark: {},
  oneLight: {},
}));

// A code block has a header with its language and a copy button; inline code
// has neither (#964).
const copyButtons = () => screen.queryAllByRole("button", { name: "Copy" });

describe("TextMessage code", () => {
  test("a fenced block without a language renders as a block", () => {
    renderWithProviders(
      <TextMessage message={"Look:\n\n```\nprint('hi')\n```"} />,
    );

    expect(copyButtons()).toHaveLength(1);
    expect(screen.getByText("text")).toBeInTheDocument();
  });

  test("a fenced block without a language holding JSON is labeled json", () => {
    renderWithProviders(<TextMessage message={'```\n{"d": 123}\n```'} />);

    expect(copyButtons()).toHaveLength(1);
    expect(screen.getByText("json")).toBeInTheDocument();
  });

  test("a fenced block without a language that only looks like JSON is text", () => {
    renderWithProviders(<TextMessage message={"```\n{not json}\n```"} />);

    expect(copyButtons()).toHaveLength(1);
    expect(screen.getByText("text")).toBeInTheDocument();
  });

  test("inline code stays inline", () => {
    renderWithProviders(<TextMessage message={"Call `print()` here."} />);

    expect(copyButtons()).toHaveLength(0);
    expect(screen.getByText("print()").tagName).toBe("CODE");
  });

  test("a fenced block with a language keeps its label", () => {
    renderWithProviders(<TextMessage message={"```python\nx = 1\n```"} />);

    expect(copyButtons()).toHaveLength(1);
    expect(screen.getByText("python")).toBeInTheDocument();
  });
});
