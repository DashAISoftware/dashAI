import React from "react";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ThemeProvider, createTheme } from "@mui/material/styles";
import { I18nextProvider } from "react-i18next";
import i18n from "../utils/i18n";
import getTheme from "../styles/theme";
import { ColorModeContext } from "../contexts/ThemeContext";

const mockColorMode = { toggleColorMode: jest.fn() };

export function renderWithProviders(ui, { route = "/" } = {}) {
  const theme = createTheme(getTheme("dark", "en"));
  return render(
    <ColorModeContext.Provider value={mockColorMode}>
      <ThemeProvider theme={theme}>
        <I18nextProvider i18n={i18n}>
          <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
        </I18nextProvider>
      </ThemeProvider>
    </ColorModeContext.Provider>
  );
}
