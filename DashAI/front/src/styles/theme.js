import QuicksandBoldWoff2 from "./fonts/Quicksand-Bold.woff2";

const getTheme = (mode) => ({
  palette: {
    mode,

    // PRIMARY - Main application color
    // Used in: primary buttons, highlighted icons, links, active elements
    primary: {
      light: "#008582",
      main: "#00BEBB",
      dark: "#002884",
      contrastText: "#fff",
    },

    // SECONDARY - Complementary secondary color
    // Used in: secondary buttons, supporting elements
    secondary: {
      light: "#6E86E8",
      main: "#6E86E8",
      dark: "#4d5da2",
      contrastText: "#000",
    },

    // DIVIDER - Divider color
    // Used in: Divider components, separators
    divider:
      mode === "dark" ? "rgba(255, 255, 255, 0.12)" : "rgba(0, 0, 0, 0.12)",

    // BACKGROUND - Background colors for different surfaces
    // Used in: page backgrounds, cards, modals, panels
    background:
      mode === "dark"
        ? {
            default: "#2e3037", // Main app background
            paper: "#121212", // Cards and modals background
            box: "#212121", // Boxes and containers (AppBar, sidebars)
          }
        : {
            default: "#f5f5f5", // Main app background
            paper: "#ffffff", // Cards and modals background
            box: "#fafafa", // Boxes and containers (AppBar, sidebars)
          },

    // TEXT - Text colors
    // Used in: Typography components, labels, paragraphs
    text:
      mode === "dark"
        ? {
            primary: "#ffffff", // Primary text (titles, important labels)
            secondary: "#b0b0b0", // Secondary text (descriptions, subtitles)
            disabled: "#757575", // Disabled text
          }
        : {
            primary: "#1a1a1a", // Primary text (titles, important labels)
            secondary: "#666666", // Secondary text (descriptions, subtitles)
            disabled: "#9e9e9e", // Disabled text
          },

    // ACTION - Interactive states
    // Used in: hover states, selected items, disabled states, focus indicators
    action:
      mode === "dark"
        ? {
            hover: "rgba(255, 255, 255, 0.08)", // Hover state for interactive elements
            selected: "rgba(255, 255, 255, 0.16)", // Selected state for items
            disabled: "rgba(255, 255, 255, 0.3)", // Disabled state opacity
            disabledBackground: "rgba(255, 255, 255, 0.12)", // Disabled background
          }
        : {
            hover: "rgba(0, 0, 0, 0.04)", // Hover state for interactive elements
            selected: "rgba(0, 0, 0, 0.08)", // Selected state for items
            disabled: "rgba(0, 0, 0, 0.26)", // Disabled state opacity
            disabledBackground: "rgba(0, 0, 0, 0.12)", // Disabled background
          },

    // ERROR - Error states
    // Used in: error messages, failed validations, critical alerts
    error: {
      main: mode === "dark" ? "#ff8383" : "#d32f2f",
    },

    // WARNING - Warning states
    // Used in: warning alerts, pending states requiring attention
    warning: {
      main: mode === "dark" ? "#f1ae61" : "#ed6c02",
    },

    // SUCCESS - Success states
    // Used in: confirmations, successful validations, completed states
    success: {
      main: "#43A047",
      light: "#4caf50",
    },

    // INFO - Informational states
    // Used in: info messages, tooltips, contextual help
    info: {
      main: "#2196f3",
      light: "#3e68ff",
    },

    // ACCENT - Custom accent colors
    // Used in: elements requiring emphasis, special details
    accent: {
      main: "#16FFFF", // Main accent color (cyan)
      cyan: "#16FFFF", // For highlights
      teal: "#00BEBB", // For featured elements
    },

    // STATUS - Experiment/job states
    // Used in: status badges, progress indicators in experiments and runs
    status: {
      notStarted: mode === "dark" ? "#626262" : "#9e9e9e", // Experiment not started
      started: "#3e68ffff", // Experiment running
      finished: "#43A047", // Experiment completed successfully
      delivered: "#3e68ffff", // Results delivered
      error: mode === "dark" ? "#A70909" : "#c62828", // Experiment error
    },

    // DATATYPE - Colors for data types in columns
    // Used in: dataset visualization, column type identification
    dataType: {
      numerical: "#00BEBB", // Numerical data (float)
      integer: "#3e68ff", // Integer data
      categorical: "#9c27b0", // Categorical data
      text: "#f1ae61", // Text/string data
      boolean: "#43A047", // Boolean data
      datetime: "#e91e63", // Date/time data
      image: "#6E86E8", // Image data
      default: "#757575", // Unknown or default type
    },

    // CHART - Colors for charts and visualizations
    // Used in: metric charts, data splits in results
    chart: {
      train: "#4caf50", // Training data
      test: "#2196f3", // Test data
      validation: "#ff9800", // Validation data
    },

    // UI - Interface elements and borders
    // Used in: borders, dividers, scrollbars, hover states
    ui:
      mode === "dark"
        ? {
            border: "#333", // Standard border
            borderLight: "#444", // Lighter border
            borderDark: "#252836", // Darker border
            panelDark: "#2C2C2C", // Dark panel
            panelMedium: "#363636", // Medium panel
            panelLight: "#2F2F2F", // Light panel
            scrollbar: "#374151", // Scrollbar color
            scrollbarHover: "#4B5563", // Scrollbar on hover
            hover: "rgba(255, 255, 255, 0.05)", // Element hover state
            divider: "rgba(255, 255, 255, 0.15)", // Dividers and separators
            box: "#212121", // Boxes and containers background
            disabled: "#2C2C2C", // Disabled elements background
          }
        : {
            border: "#e0e0e0", // Standard border
            borderLight: "#f0f0f0", // Lighter border
            borderDark: "#d0d0d0", // Darker border
            panelDark: "#f5f5f5", // Light panel
            panelMedium: "#fafafa", // Medium panel
            panelLight: "#ffffff", // Lightest panel
            scrollbar: "#bdbdbd", // Scrollbar color
            scrollbarHover: "#9e9e9e", // Scrollbar on hover
            hover: "rgba(0, 0, 0, 0.04)", // Element hover state
            divider: "rgba(0, 0, 0, 0.12)", // Dividers and separators
            box: "#fafafa", // Boxes and containers background
            disabled: "#f5f5f5", // Disabled elements background
          },
  },
  typography: {
    fontFamily: "Quicksand-Bold",
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: `
        @font-face {
          font-family: 'Quicksand-Bold';
          src: url(${QuicksandBoldWoff2});
        }
        /* custom scrollbar */

        ::-webkit-scrollbar {
          width: 12px;
        }
        /* Track */
        ::-webkit-scrollbar-track {
            -webkit-box-shadow: inset 0 0 6px rgba(0,0,0,0.3);
            -webkit-border-radius: 10px;
            border-radius: 10px;
        }

        /* Handle */
        ::-webkit-scrollbar-thumb {
            -webkit-border-radius: 10px;
            border-radius: 10px;
            background: ${mode === "dark" ? "rgba(0, 0, 0, 0.8)" : "rgba(0, 0, 0, 0.3)"};
            -webkit-box-shadow: inset 0 0 6px rgba(0,0,0,0.5);
        }
        ::-webkit-scrollbar-thumb:window-inactive {
                background: ${mode === "dark" ? "rgba(0,0,0,0.4)" : "rgba(0,0,0,0.2)"};
        }
      `,
    },

    MuiDataGrid: {
      styleOverrides: {
        root: {
          "--DataGrid-containerBackground": "transparent",
          "& .MuiDataGrid-columnSeparator": {
            visibility: "hidden",
          },
          "& .MuiDataGrid-columnHeader:hover .MuiDataGrid-columnSeparator": {
            visibility: "visible",
          },
        },
        columnHeader: {
          backgroundColor: "transparent",
        },
      },
    },
  },
});

export default getTheme;
