import React from "react";
import PropTypes from "prop-types";
import {
  Paper,
  CircularProgress,
  Button,
  ButtonGroup,
  Typography,
} from "@mui/material";
import { MaterialReactTable, useMaterialReactTable } from "material-react-table";
import { MRT_Localization_ES } from "material-react-table/locales/es";
import { MRT_Localization_EN } from "material-react-table/locales/en";
import { useTheme } from "@mui/material/styles";
import ResultsDetails from "./ResultsDetails";
import { PlayArrow } from "@mui/icons-material";
import { LoadingButton } from "@mui/lab";
import { useTranslation } from "react-i18next";

function ResultsTableLayout({
  rows,
  columns,
  showRunResults,
  loading,
  selectedRun,
  handleCloseRunResults,
  columnVisibilityModel,
  handleExecuteRuns,
  handleRun,
}) {
  const { t, i18n } = useTranslation(["models"]);
  const theme = useTheme();
  const localization = i18n.language.startsWith("es")
    ? MRT_Localization_ES
    : MRT_Localization_EN;

  const table = useMaterialReactTable({
    columns,
    data: rows,
    state: {
      isLoading: loading,
      columnVisibility: columnVisibilityModel,
    },
    enableRowSelection: false,
    disableRowSelectionOnClick: true,
    enablePagination: true,
    initialState: {
      pagination: { pageSize: 10, pageIndex: 0 },
      density: "compact",
    },
    localization,
    enableFullScreenToggle: false,
    enableDensityToggle: false,
    muiTableProps: {
      "data-tour": "results-table",
    },
    muiTableBodyCellProps: {
      sx: {
        "&:focus": { outline: "none" },
      },
    },
    mrtTheme: (theme) => ({
      baseBackgroundColor: theme.palette.background.paper,
    }),
    muiTablePaperProps: {
      elevation: 0,
      sx: { border: "none" },
    },
  });

  return (
    <Paper
      sx={{
        p: 4,
      }}
    >
      {!loading ? (
        <>
          <ButtonGroup
            sx={{
              display: "flex",
              justifyContent: "space-between",
              pb: 4,
              pt: 0,
            }}
          >
            <Typography variant="h6">Models Results</Typography>
            <LoadingButton
              data-tour="runner-dialog-start"
              variant="contained"
              loading={rows.every(
                (run) => run.status === 1 || run.status === 2,
              )}
              endIcon={<PlayArrow />}
              onClick={handleExecuteRuns}
              style={{ borderRadius: 4 }}
            >
              {t("models:button.runAllModels")}
            </LoadingButton>
          </ButtonGroup>
          <MaterialReactTable table={table} />
        </>
      ) : (
        <CircularProgress color="inherit" />
      )}

      {showRunResults && (
        <ResultsDetails
          run={selectedRun}
          onClose={handleCloseRunResults}
          handleRun={handleRun}
        />
      )}
    </Paper>
  );
}

ResultsTableLayout.propTypes = {
  experimentId: PropTypes.string,
  rows: PropTypes.array,
  columns: PropTypes.array,
  showRunResults: PropTypes.bool,
  loading: PropTypes.bool,
  selectedRunId: PropTypes.number,
  handleCloseRunResults: PropTypes.func,
  columnVisibilityModel: PropTypes.objectOf(PropTypes.bool),
  handleExecuteRuns: PropTypes.func,
  handleRun: PropTypes.func,
};

export default ResultsTableLayout;
