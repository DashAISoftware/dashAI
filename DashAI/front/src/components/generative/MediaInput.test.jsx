import React from "react";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import { MediaInput } from "./MediaInput";

// The composer empties as soon as a message is sent. When the send fails
// before the turn exists (the backend refuses it), nothing on screen holds
// the message any more, so the composer gets it back (#969).

beforeAll(() => {
  // jsdom has no object URLs; the previews only need a string.
  global.URL.createObjectURL = jest.fn(() => "blob:preview");
  global.URL.revokeObjectURL = jest.fn();
});

const renderInput = (onSendMessage, inputsCardinality = { str: 1 }) =>
  renderWithProviders(
    <MediaInput
      onSendMessage={onSendMessage}
      inputsCardinality={inputsCardinality}
    />,
  );

const typeAndSend = (text) => {
  const box = screen.getByRole("textbox");
  fireEvent.change(box, { target: { value: text } });
  fireEvent.keyDown(box, { key: "Enter" });
  return box;
};

test("a message the backend refuses goes back to the composer", async () => {
  renderInput(() => Promise.reject(new Error("refused")));
  const box = typeAndSend("my long question");

  await waitFor(() => expect(box).toHaveValue("my long question"));
});

test("a sent message leaves the composer empty", async () => {
  renderInput(() => Promise.resolve());
  const box = typeAndSend("my question");

  await waitFor(() => expect(box).toHaveValue(""));
});

test("an image attached to a refused message is attached again", async () => {
  renderInput(() => Promise.reject(new Error("refused")), {
    str: 1,
    Image: 1,
  });
  const file = new File(["x"], "cat.png", { type: "image/png" });
  const fileInput = document.querySelector('input[accept="image/*"]');
  fireEvent.change(fileInput, { target: { files: [file] } });
  expect(screen.getByAltText("Image preview 0")).toBeInTheDocument();

  typeAndSend("what is this?");

  expect(await screen.findByAltText("Image preview 0")).toBeInTheDocument();
  expect(screen.getByRole("textbox")).toHaveValue("what is this?");
});
