import React from "react";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";
import ImportGenerativeSessionButton from "./ImportGenerativeSessionButton";
import { importGenerativeSession } from "../../api/session";

jest.mock("notistack", () => {
  const snackbar = { enqueueSnackbar: jest.fn(), closeSnackbar: jest.fn() };
  return { useSnackbar: () => snackbar };
});

const mockNavigate = jest.fn();
jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useNavigate: () => mockNavigate,
}));

jest.mock("../../api/session", () => ({
  importGenerativeSession: jest.fn(),
}));

beforeEach(() => jest.clearAllMocks());

// Opening the session remounts the session list and this button, so a report
// shown before navigating would vanish unread.
test("a session with notices opens only once the report is closed", async () => {
  importGenerativeSession.mockResolvedValue({
    session_id: 4,
    task_name: "TextToImageGenerationTask",
    session_name: "Images (2)",
    renamed: true,
    warnings: [],
    needs_download: [
      { name: "StableDiffusion2", display_name: "Stable Diffusion 2" },
    ],
  });
  const { container } = renderWithProviders(<ImportGenerativeSessionButton />);
  fireEvent.change(container.querySelector('input[type="file"]'), {
    target: { files: [new File(["zip"], "s.dashai")] },
  });

  await screen.findByText(/Stable Diffusion 2/);
  expect(mockNavigate).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("button", { name: /got it/i }));
  await waitFor(() =>
    expect(mockNavigate).toHaveBeenCalledWith("/app/generative/sessions/4"),
  );
});
