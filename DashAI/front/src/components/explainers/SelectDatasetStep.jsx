import React, { useState, useEffect, useMemo } from "react";
import PropTypes from "prop-types";

import {
  Alert,
  AlertTitle,
  Grid,
  Link,
  Paper,
  Typography,
} from "@mui/material";
import {
  MaterialReactTable,
  useMaterialReactTable,
} from "material-react-table";
import { useTheme } from "@mui/material/styles";
import { useSnackbar } from "notistack";
import { Link as RouterLink } from "react-router-dom";
import { Trans, useTranslation } from "react-i18next";
import { useTableLocalization } from "../../utils/useTableLocalization";

import {
  getDatasets as getDatasetsRequest,
  getDatasetInfo,
} from "../../api/datasets";
import { validateDataset as validateDatasetRequest } from "../../api/explainer";
import { getRunById } from "../../api/run";
import { getModelSessionById } from "../../api/modelSession";
import { formatDate } from "../../utils";
import { SplitSelector } from "./SplitSelector";
import NoteBox from "../notebooks/NoteBox";

export default function SelectDatasetStep({
  newExpl,
  setNewExpl,
  setNextEnabled,
}) {
  const { enqueueSnackbar } = useSnackbar();
  const [loading, setLoading] = useState(true);
  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState(false);
  const [isValidDataset, setIsValidDataset] = useState(false);
  const [requestError, setRequestError] = useState(false);
  const [totalRows, setTotalRows] = useState(0);
  const [splits, setSplits] = useState({
    train: 0,
    test: 0,
    validation: 0,
    all: 1,
  });
  const { t } = useTranslation(["explainers", "common"]);
  const theme = useTheme();
  const localization = useTableLocalization();

  const columns = useMemo(
    () => [
      {
        accessorKey: "name",
        header: "Name",
      },
      {
        accessorKey: "created",
        header: "Created",
        Cell: ({ cell }) => formatDate(cell.getValue()),
      },
      {
        accessorKey: "last_modified",
        header: "Last modified",
        Cell: ({ cell }) => formatDate(cell.getValue()),
      },
    ],
    [],
  );

  const getDatasets = async () => {
    setLoading(true);
    try {
      const datasets = await getDatasetsRequest();
      setDatasets(datasets);
    } catch (error) {
      enqueueSnackbar(t("explainers:error.fetchDatasets"), {
        variant: "error",
      });
      setRequestError(true);
      if (error.response) {
        console.error("Response error:", error.message);
      } else if (error.request) {
        console.error("Request error", error.request);
      } else {
        console.error("Unknown Error", error.message);
      }
    } finally {
      setLoading(false);
    }
  };

  const validateDataset = async () => {
    try {
      const validation = await validateDatasetRequest(
        newExpl.run_id,
        selectedDatasetId,
      );
      setIsValidDataset(validation.dataset_status === "valid");
      if (validation.dataset_status === "invalid") {
        enqueueSnackbar(t("explainers:error.invalidDataset"), {
          variant: "error",
        });
      }
    } catch (error) {
      enqueueSnackbar(t("explainers:error.validateDataset"), {
        variant: "error",
      });
      if (error.response) {
        console.error("Response error:", error.message);
      } else if (error.request) {
        console.error("Request error", error.request);
      } else {
        console.error("Unknown Error", error.message);
      }
    }
  };

  const getTotalRows = async () => {
    if (selectedDatasetId) {
      try {
        const datasetInfo = await getDatasetInfo(selectedDatasetId);
        setTotalRows(datasetInfo.total_rows);
      } catch {
        console.error(`Error fetching dataset info for ${selectedDatasetId}`);
      }
    }
  };

  // fetch datasets when the component is mounting
  useEffect(() => {
    getDatasets();
  }, []);

  useEffect(() => {
    getTotalRows();
  }, [selectedDatasetId]);

  const getRuninfo = async () => {
    if (newExpl.run_id) {
      try {
        const run = await getRunById(newExpl.run_id);
        const experiment = await getModelSessionById(run.model_session_id);
        const splitsExperiment = JSON.parse(experiment.splits);
        setSplits((prev) => ({
          ...prev,
          train: splitsExperiment["train"],
          test: splitsExperiment["test"],
          validation: splitsExperiment["validation"],
        }));
      } catch {
        console.error(`Error fetching run info for ${newExpl.run_id}`);
      }
    }
  };

  useEffect(() => {
    getRuninfo();
  }, [newExpl.run_id]);

  const handleRowClick = (row) => {
    setSelectedDatasetId(row.original.id);
  };

  const datasetsTable = useMaterialReactTable({
    columns,
    data: datasets,
    muiTableBodyCellProps: { sx: { whiteSpace: "pre" } },
    enableRowSelection: false,
    muiTableBodyRowProps: ({ row }) => ({
      onClick: () => handleRowClick(row),
      sx: {
        cursor: "pointer",
        ...(row.original.id === selectedDatasetId && {
          backgroundColor: theme.palette.accent.amberDim,
          borderLeft: `3px solid ${theme.palette.primary.main}`,
          "&:hover td": {
            backgroundColor: "transparent",
          },
        }),
      },
    }),
    state: { isLoading: loading },
    enableGlobalFilter: false,
    enableColumnFilters: false,
    enableSorting: true,
    enablePagination: true,
    enableTopToolbar: false,
    muiPaginationProps: { showRowsPerPage: false },
    initialState: {
      pagination: { pageSize: 10, pageIndex: 0 },
      density: "compact",
    },
    localization,
  });

  useEffect(() => {
    if (selectedDatasetId) {
      validateDataset();
    }
  }, [selectedDatasetId]);

  useEffect(() => {
    if (isValidDataset && selectedDatasetId) {
      setNewExpl((prevExpl) => ({
        ...prevExpl,
        dataset_id: selectedDatasetId,
      }));
      setNextEnabled(true);
    } else {
      setNextEnabled(false);
    }
  }, [isValidDataset, selectedDatasetId]);

  return (
    <React.Fragment>
      {/* Title and new datasets button */}
      <Grid
        container
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ mb: 4 }}
      >
        <Typography variant="subtitle1" component="h3">
          {t("explainers:label.selectDatasetToExplain")}
        </Typography>
      </Grid>

      {/* Datasets Table */}

      {datasets.length === 0 && !loading && !requestError && (
        <React.Fragment>
          <Alert severity="warning" sx={{ mb: 4 }}>
            <Trans i18nKey="explainers:label.noDatasetsAvailable">
              <AlertTitle>There are no datasets available.</AlertTitle>
              Go to
              <Link component={RouterLink} to="/app/data?action=upload">
                data tab
              </Link>
              to upload one first.
            </Trans>
          </Alert>
        </React.Fragment>
      )}
      <Paper>
        <MaterialReactTable table={datasetsTable} />
      </Paper>

      {selectedDatasetId && isValidDataset && (
        <>
          <SplitSelector
            totalRows={totalRows}
            splits={splits}
            onSelectionChange={(scope) => {
              setNewExpl((prevExpl) => ({ ...prevExpl, scope }));
            }}
          />
          <NoteBox message={t("explainers:label.datasetSelection")} />
        </>
      )}
    </React.Fragment>
  );
}

SelectDatasetStep.propTypes = {
  newExpl: PropTypes.shape({
    run_id: PropTypes.string,
    name: PropTypes.string,
    explainer_name: PropTypes.string,
    dataset_id: PropTypes.number,
    parameters: PropTypes.object,
    fit_parameters: PropTypes.object,
  }),
  setNewExpl: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
};
