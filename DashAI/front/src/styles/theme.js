const getTheme = (mode) => ({
  palette: {
    mode,

    primary: {
      light: mode === "dark" ? "#f5b94a" : "#d98200",
      main: mode === "dark" ? "#ef9f27" : "#b86e00",
      dark: mode === "dark" ? "#c47d0e" : "#8f5200",
      contrastText: mode === "dark" ? "#0c0c0a" : "#ffffff",
    },

    secondary: {
      light: "#2ec98a",
      main: "#1d9e75",
      dark: "#14735a",
      contrastText: "#ffffff",
    },

    divider: mode === "dark" ? "rgba(239,159,39,0.10)" : "rgba(0,0,0,0.10)",

    background:
      mode === "dark"
        ? {
            default: "#0c0c0a",
            paper: "#111110",
            box: "#0f0f0d",
          }
        : {
            default: "#f5f5f5",
            paper: "#ffffff",
            box: "#fafafa",
          },

    text:
      mode === "dark"
        ? {
            primary: "#f2ede2",
            secondary: "rgba(232,228,217,0.75)",
            disabled: "rgba(232,228,217,0.45)",
          }
        : {
            primary: "#111111",
            secondary: "rgba(17,17,17,0.5)",
            disabled: "rgba(17,17,17,0.3)",
          },

    action:
      mode === "dark"
        ? {
            hover: "rgba(239,159,39,0.04)",
            selected: "rgba(239,159,39,0.08)",
            disabled: "rgba(232,228,217,0.3)",
            disabledBackground: "rgba(232,228,217,0.12)",
          }
        : {
            hover: "rgba(0,0,0,0.04)",
            selected: "rgba(0,0,0,0.08)",
            disabled: "rgba(0,0,0,0.26)",
            disabledBackground: "rgba(0,0,0,0.12)",
          },

    error: {
      main: mode === "dark" ? "#ff8383" : "#d32f2f",
    },
    warning: {
      main: mode === "dark" ? "#fbc02d" : "#f9a825",
    },
    success: {
      main: "#43A047",
      light: "#4caf50",
    },
    info: {
      main: "#2196f3",
      light: "#3e68ff",
    },

    // Card accent colors — same in both modes
    accent: {
      amber: "#ef9f27",
      amberDim: "rgba(239,159,39,0.12)",
      amberBorder: "rgba(239,159,39,0.22)",
      amberGlow: "rgba(239,159,39,0.04)",
      teal: "#1d9e75",
      tealDim: "rgba(29,158,117,0.10)",
      tealBorder: "rgba(29,158,117,0.22)",
      tealGlow: "rgba(29,158,117,0.04)",
      purple: "#9b7de8",
      purpleDim: "rgba(155,125,232,0.10)",
      purpleBorder: "rgba(155,125,232,0.22)",
      purpleGlow: "rgba(155,125,232,0.04)",
      coral: "#d85a30",
      coralDim: "rgba(216,90,48,0.10)",
      coralBorder: "rgba(216,90,48,0.22)",
      coralGlow: "rgba(216,90,48,0.04)",
    },

    status: {
      notStarted: mode === "dark" ? "#626262" : "#9e9e9e",
      started: "#3e68ffff",
      finished: "#43A047",
      delivered: "#3e68ffff",
      error: mode === "dark" ? "#A70909" : "#c62828",
    },

    dataType: {
      numerical: "#00BEBB", // Numerical data (float)
      integer: "#5c6bc0", // Integer data
      categorical: "#9c27b0", // Categorical data
      text: "#d4a054", // Text/string data
      boolean: "#8bc34a", // Boolean data
      datetime: "#e91e63", // Date/time data
      image: "#6E86E8", // Image data
      default: "#757575", // Unknown or default type
    },

    chart: {
      train: "#66bb6a",
      test: "#42a5f5",
      validation: "#ff9800",
      palette: [
        "#66bb6a",
        "#42a5f5",
        "#ff9800",
        "#ab47bc",
        "#ef5350",
        "#26a69a",
        "#8d6e63",
        "#78909c",
      ],
    },

    ui:
      mode === "dark"
        ? {
            border: "rgba(239,159,39,0.10)",
            borderLight: "rgba(239,159,39,0.06)",
            borderMed: "rgba(239,159,39,0.18)",
            borderDark: "rgba(239,159,39,0.22)",
            panelDark: "#0f0f0d",
            panelMedium: "#111110",
            panelLight: "#161614",
            scrollbar: "rgba(239,159,39,0.25)",
            scrollbarHover: "rgba(239,159,39,0.4)",
            hover: "rgba(239,159,39,0.03)",
            divider: "rgba(239,159,39,0.10)",
            box: "#0f0f0d",
            disabled: "#161614",
            rowDisabled: "rgba(255,255,255,0.04)",
          }
        : {
            border: "rgba(0,0,0,0.10)",
            borderLight: "rgba(0,0,0,0.06)",
            borderMed: "rgba(0,0,0,0.16)",
            borderDark: "rgba(0,0,0,0.22)",
            panelDark: "#f5f5f5",
            panelMedium: "#fafafa",
            panelLight: "#ffffff",
            scrollbar: "#bdbdbd",
            scrollbarHover: "#9e9e9e",
            hover: "rgba(0,0,0,0.04)",
            divider: "rgba(0,0,0,0.10)",
            box: "#fafafa",
            disabled: "#f5f5f5",
            rowDisabled: "rgba(0,0,0,0.04)",
          },
  },

  typography: {
    fontFamily: '"IBM Plex Sans", sans-serif',

    // --- ESCALA DE TITULARES ---
    h1: { fontSize: "28px", fontWeight: 700, letterSpacing: "-0.01em" },
    h2: { fontSize: "22px", fontWeight: 600, letterSpacing: "-0.01em" },
    h3: { fontSize: "20px", fontWeight: 600, letterSpacing: "-0.01em" },
    h4: { fontSize: "17px", fontWeight: 600, letterSpacing: "-0.01em" },
    h5: { fontSize: "16px", fontWeight: 600 },
    h6: { fontSize: "14px", fontWeight: 600 },

    // --- ESCALA DE CUERPO ---
    subtitle1: { fontSize: "17px", fontWeight: 400 }, // Parámetros principales
    subtitle2: { fontSize: "16px", fontWeight: 400 }, // Texto destacado
    body1: { fontSize: "14px", fontWeight: 400, lineHeight: 1.6 }, // Cuerpo / párrafos
    body2: { fontSize: "12px", fontWeight: 400, lineHeight: 1.5 }, // Texto auxiliar / labels
    caption: {
      fontFamily: '"IBM Plex Mono", monospace',
      fontSize: "12px",
      fontWeight: 400,
    }, // Información secundaria, captions, code

    // --- VARIANTES UI FUNCIONALES ---
    navItem: { fontSize: "12px", fontWeight: 400 }, // Sidebar links/Navigation
    tabLabel: {
      fontFamily: '"IBM Plex Mono", monospace',
      fontSize: "10px",
      letterSpacing: "0.12em",
      textTransform: "uppercase",
    }, // Navigation tabs
    sectionLabel: {
      fontFamily: '"IBM Plex Mono", monospace',
      fontSize: "9px",
      letterSpacing: "0.2em",
      textTransform: "uppercase",
    }, // Sidebar section headers
    statusBadge: {
      fontFamily: '"IBM Plex Mono", monospace',
      fontSize: "8.5px",
      letterSpacing: "0.12em",
      textTransform: "uppercase",
    },
    button: {
      fontSize: "14px",
      fontWeight: 500,
      letterSpacing: "-0.01em",
      textTransform: "uppercase",
    },
  },

  components: {
    MuiCssBaseline: {
      styleOverrides: `
        ::-webkit-scrollbar { width: 12px; }
        ::-webkit-scrollbar-track {
          -webkit-box-shadow: inset 0 0 6px rgba(0,0,0,0.3);
          -webkit-border-radius: 10px;
          border-radius: 10px;
        }
        ::-webkit-scrollbar-thumb {
          -webkit-border-radius: 10px;
          border-radius: 10px;
          background: ${
            mode === "dark" ? "rgba(239,159,39,0.25)" : "rgba(0,0,0,0.3)"
          };
          -webkit-box-shadow: inset 0 0 6px rgba(0,0,0,0.5);
        }
        ::-webkit-scrollbar-thumb:window-inactive {
          background: ${
            mode === "dark" ? "rgba(239,159,39,0.12)" : "rgba(0,0,0,0.2)"
          };
        }
      `,
    },
  },
});

export default getTheme;
