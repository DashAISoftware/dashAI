import { dataGridLocales } from "../utils/i18n/datagridLocale";

const getTheme = (mode, language) => ({
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
      main: mode === "dark" ? "#f1ae61" : "#ed6c02",
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
      numerical: "#ef9f27",
      integer: "#3e68ff",
      categorical: "#9c27b0",
      text: "#f1ae61",
      boolean: "#43A047",
      datetime: "#e91e63",
      image: "#9b7de8",
      default: "#757575",
    },

    chart: {
      train: "#4caf50",
      test: "#2196f3",
      validation: "#ff9800",
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
          },
  },

  typography: {
    fontFamily: '"IBM Plex Sans", sans-serif',
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

    MuiDataGrid: {
      styleOverrides: {
        root: {
          "--DataGrid-containerBackground": "transparent",
          "& .MuiDataGrid-columnSeparator": { visibility: "hidden" },
          "& .MuiDataGrid-columnHeader:hover .MuiDataGrid-columnSeparator": {
            visibility: "visible",
          },
        },
        columnHeader: { backgroundColor: "transparent" },
      },
      defaultProps: {
        localeText: dataGridLocales[language] ?? dataGridLocales.en,
      },
    },
  },
});

export default getTheme;
