import QuicksandBoldWoff2 from "./fonts/Quicksand-Bold.woff2";

const theme = {
  palette: {
    mode: "dark",

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

    // BACKGROUND - Background colors for different surfaces
    // Used in: page backgrounds, cards, modals, panels
    background: {
      default: "#2e3037", // Main app background
      paper: "#121212", // Cards and modals background
      box: "#212121", // Boxes and containers (AppBar, sidebars)
    },

    // TEXT - Text colors
    // Used in: Typography components, labels, paragraphs
    text: {
      primary: "#ffffff", // Primary text (titles, important labels)
      secondary: "#b0b0b0", // Secondary text (descriptions, subtitles)
    },

    // ERROR - Error states
    // Used in: error messages, failed validations, critical alerts
    error: {
      main: "#ff8383",
    },

    // WARNING - Warning states
    // Used in: warning alerts, pending states requiring attention
    warning: {
      main: "#f1ae61",
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
      cyan: "#16FFFF", // For highlights
      teal: "#00BEBB", // For featured elements
    },

    // STATUS - Experiment/job states
    // Used in: status badges, progress indicators in experiments and runs
    status: {
      notStarted: "#626262", // Experiment not started
      started: "#3e68ffff", // Experiment running
      finished: "#43A047", // Experiment completed successfully
      delivered: "#3e68ffff", // Results delivered
      error: "#A70909", // Experiment error
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
    ui: {
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
            background: rgba(0, 0, 0, 0.8);
            -webkit-box-shadow: inset 0 0 6px rgba(0,0,0,0.5);
        }
        ::-webkit-scrollbar-thumb:window-inactive {
                background: rgba(0,0,0,0.4);
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
};

export default theme;
