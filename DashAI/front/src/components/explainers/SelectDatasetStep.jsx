import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";

import {
  Alert,
  AlertTitle,
  Grid,
  Link,
  Paper,
  Typography,
} from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import { useSnackbar } from "notistack";
import { Link as RouterLink } from "react-router-dom";
import { Trans, useTranslation } from "react-i18next";

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

const columns = [
  {
    field: "name",
    headerName: "Name",
    minWidth: 250,
    editable: false,
  },
  {
    field: "created",
    headerName: "Created",
    minWidth: 200,
    type: Date,
    valueGetter: (value) => formatDate(value),

    editable: false,
  },
  {
    field: "last_modified",
    headerName: "Last modified",
    minWidth: 200,
    type: Date,
    valueGetter: (value) => formatDate(value),
    editable: false,
  },
];

export default function SelectDatasetStep({
  newExpl,
  setNewExpl,
  setNextEnabled,
}) {
  const { enqueueSnackbar } = useSnackbar();
  const [loading, setLoading] = useState(true);
  const [datasets, setDatasets] = useState([]);
  const [rowSelectedDataset, setRowSelectedDataset] = useState([]);
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

  const validateDataset = async (datasetId) => {
    try {
      const validation = await validateDatasetRequest(
        newExpl.run_id,
        datasetId,
      );
      const valid = validation.dataset_status === "valid";
      setIsValidDataset(valid);
      if (!valid) {
        enqueueSnackbar(t("explainers:error.invalidDataset"), {
          variant: "error",
        });
      }
      return valid;
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
      return false;
    }
  };

  const getTotalRows = async (datasetId) => {
    if (datasetId) {
      try {
        const datasetInfo = await getDatasetInfo(datasetId);
        setTotalRows(datasetInfo.total_rows);
      } catch {
        console.error(`Error fetching dataset info for ${datasetId}`);
      }
    }
  };

  // fetch datasets when the component is mounting
  useEffect(() => {
    getDatasets();
  }, []);

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

  // Prop-driven effect — cannot move to handler
  useEffect(() => {
    getRuninfo();
  }, [newExpl.run_id]);

  const handleDatasetRowSelection = async (newRowSelectionModel) => {
    setRowSelectedDataset(newRowSelectionModel);
    if (newRowSelectionModel.length > 0) {
      const id = newRowSelectionModel[0];
      const dataset = datasets.find((d) => d.id === id);
      if (!dataset) return;
      setSelectedDatasetId(dataset.id);
      await getTotalRows(dataset.id);
      const valid = await validateDataset(dataset.id);
      if (valid) {
        setNewExpl((prevExpl) => ({
          ...prevExpl,
          dataset_id: dataset.id,
        }));
        setNextEnabled(true);
      } else {
        setNextEnabled(false);
      }
    } else {
      setSelectedDatasetId(false);
      setIsValidDataset(false);
      setNextEnabled(false);
    }
  };

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
          <Alert severity="warning" sx={{ mb: 2 }}>
            <Trans i18nKey="explainers:label.noDatasetsAvailable">
              <AlertTitle>There are no datasets available.</AlertTitle>
              Go to
              <Link component={RouterLink} to="/app/data">
                data tab
              </Link>
              to upload one first.
            </Trans>
          </Alert>
        </React.Fragment>
      )}
      <Paper>
        <DataGrid
          rows={datasets}
          columns={columns}
          initialState={{
            pagination: {
              paginationModel: {
                pageSize: 10,
              },
            },
          }}
          onRowSelectionModelChange={handleDatasetRowSelection}
          rowSelectionModel={rowSelectedDataset}
          density="compact"
          pageSizeOptions={[10]}
          loading={loading}
          autoHeight
          hideFooterSelectedRowCount
        />
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
