import React from "react";
import PropTypes from "prop-types";
import {
  Paper,
  Alert,
  AlertTitle,
  CircularProgress,
  Button,
  ButtonGroup,
  Typography,
} from "@mui/material";
import { DataGrid, GridToolbar } from "@mui/x-data-grid";
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
  columnGroupingModel,
  handleExecuteRuns,
  handleRun,
}) {
  const { t } = useTranslation(["models"]);

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
                (run) => run.status === "Delivered" || run.status === "Started",
              )}
              endIcon={<PlayArrow />}
              onClick={handleExecuteRuns}
              style={{ borderRadius: 4 }}
            >
              {t("models:button.runAllModels")}
            </LoadingButton>
          </ButtonGroup>
          <DataGrid
            rows={rows}
            columns={columns}
            initialState={{
              pagination: {
                paginationModel: {
                  pageSize: 10,
                },
              },
              columns: {
                columnVisibilityModel,
              },
            }}
            experimentalFeatures={{ columnGrouping: true }}
            columnGroupingModel={columnGroupingModel}
            pageSizeOptions={[10]}
            density="compact"
            disableRowSelectionOnClick
            autoHeight
            sx={{
              ".MuiDataGrid-cell:focus": {
                outline: "none",
              },
              "& .MuiDataGrid-row:hover": {},
            }}
            data-tour="results-table"
          />
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
  columnGroupingModel: PropTypes.array,
};

export default ResultsTableLayout;
