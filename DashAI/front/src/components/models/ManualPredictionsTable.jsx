import React, { useState, useEffect, useCallback, useMemo } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Typography,
  CircularProgress,
  IconButton,
  Tooltip,
} from "@mui/material";
import { Delete as DeleteIcon } from "@mui/icons-material";
import { useTranslation } from "react-i18next";
import { useSnackbar } from "notistack";
import DatasetTable from "../notebooks/dataset/DatasetTable";
import DeleteConfirmationModal from "../threeSectionLayout/DeleteConfirmationModal";
import { getDatasetFile, getDatasetTypesByFilePath } from "../../api/datasets";
import { deletePrediction } from "../../api/predict";
import {
  getTargetDecimals,
  formatPredictionRows,
} from "../../utils/predictionFormat";

// Manual predictions are entered by hand, so each one only ever produces a
// handful of rows — fetching the full result in one call (instead of the
// paginated flow used for dataset predictions) is safe here.
const FETCH_ALL_PAGE_SIZE = 10000;

function applyFilter(rows, filterModel) {
  if (!filterModel?.items?.length) return rows;
  return rows.filter((row) =>
    filterModel.items.every(({ field, operator, value }) => {
      const cell = row[field];
      switch (operator) {
        case "isEmpty":
          return cell === null || cell === undefined || cell === "";
        case "isNotEmpty":
          return cell !== null && cell !== undefined && cell !== "";
        case "equals":
          return String(cell) === String(value);
        case "contains":
          return String(cell ?? "")
            .toLowerCase()
            .includes(String(value ?? "").toLowerCase());
        case "startsWith":
          return String(cell ?? "")
            .toLowerCase()
            .startsWith(String(value ?? "").toLowerCase());
        case "endsWith":
          return String(cell ?? "")
            .toLowerCase()
            .endsWith(String(value ?? "").toLowerCase());
        case "greaterThan":
          return Number(cell) > Number(value);
        case "greaterThanOrEqualTo":
          return Number(cell) >= Number(value);
        case "lessThan":
          return Number(cell) < Number(value);
        case "lessThanOrEqualTo":
          return Number(cell) <= Number(value);
        case "between": {
          const [min, max] = value ?? [];
          const num = Number(cell);
          if (min != null && String(min).trim() !== "" && num < Number(min))
            return false;
          if (max != null && String(max).trim() !== "" && num > Number(max))
            return false;
          return true;
        }
        default:
          return true;
      }
    }),
  );
}

function applySort(rows, sortModel) {
  if (!sortModel?.length) return rows;
  const { id, desc } = sortModel[0];
  const sorted = [...rows].sort((a, b) => {
    const av = a[id];
    const bv = b[id];
    if (av == null && bv == null) return 0;
    if (av == null) return -1;
    if (bv == null) return 1;
    if (typeof av === "number" && typeof bv === "number") return av - bv;
    return String(av).localeCompare(String(bv));
  });
  return desc ? sorted.reverse() : sorted;
}

export default function ManualPredictionsTable({
  predictions,
  displayNumbers,
  targetColumn,
  datasetSample,
  onDelete,
}) {
  const { t, i18n } = useTranslation(["prediction", "common"]);
  const { enqueueSnackbar } = useSnackbar();
  const [allRows, setAllRows] = useState([]);
  const [columnTypes, setColumnTypes] = useState({});
  const [loading, setLoading] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const predictionLabel = t("prediction:label.prediction");
  const createdLabel = t("common:created");

  const finishedPredictions = useMemo(
    () => predictions.filter((p) => p.status === 3),
    [predictions],
  );
  const runningPredictions = useMemo(
    () => predictions.filter((p) => p.status === 1 || p.status === 2),
    [predictions],
  );

  const refetchRows = useCallback(() => {
    if (finishedPredictions.length === 0) {
      setAllRows([]);
      setColumnTypes({});
      setLoading(false);
      return;
    }

    setLoading(true);
    const targetDecimals = getTargetDecimals(datasetSample, targetColumn);

    Promise.all(
      finishedPredictions.map((prediction) =>
        getDatasetFile(prediction.results_path, 0, FETCH_ALL_PAGE_SIZE).then(
          (data) => {
            const formatted = formatPredictionRows(
              data.rows ?? [],
              targetColumn,
              targetDecimals,
            );
            return formatted.map((row) => ({
              [`${predictionLabel} #`]: displayNumbers.get(prediction.id),
              [createdLabel]: new Date(prediction.created).toLocaleString(
                i18n.language,
              ),
              ...row,
              __predictionId: prediction.id,
            }));
          },
        ),
      ),
    )
      .then((groups) => setAllRows(groups.flat()))
      .catch(() => setAllRows([]))
      .finally(() => setLoading(false));

    getDatasetTypesByFilePath(finishedPredictions[0].results_path)
      .then((types) => setColumnTypes(types))
      .catch(() => {});
  }, [
    finishedPredictions,
    targetColumn,
    datasetSample,
    displayNumbers,
    predictionLabel,
    createdLabel,
    i18n.language,
  ]);

  useEffect(() => {
    refetchRows();
  }, [refetchRows]);

  const extendedColumnTypes = useMemo(
    () => ({
      [`${predictionLabel} #`]: "Integer",
      [createdLabel]: "Categorical",
      ...columnTypes,
    }),
    [columnTypes, predictionLabel, createdLabel],
  );

  const fetchPage = useCallback(
    async (page, pageSize, filterModel, sortModel) => {
      let rows = applyFilter(allRows, filterModel);
      rows = applySort(rows, sortModel);
      const total = rows.length;
      const start = page * pageSize;
      return { rows: rows.slice(start, start + pageSize), total };
    },
    [allRows],
  );

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    try {
      await deletePrediction(deleteTarget);
      enqueueSnackbar(t("prediction:message.deletedSuccessfully"), {
        variant: "success",
      });
      setDeleteTarget(null);
      if (onDelete) onDelete();
    } catch (error) {
      console.error("Error deleting prediction:", error);
      enqueueSnackbar(t("prediction:error.errorDeleting"), {
        variant: "error",
      });
    }
  };

  const rowActions = useCallback(
    (row) => (
      <Tooltip title={t("common:delete")}>
        <IconButton
          size="small"
          color="error"
          onClick={() => setDeleteTarget(row.__predictionId)}
        >
          <DeleteIcon fontSize="small" />
        </IconButton>
      </Tooltip>
    ),
    [t],
  );

  if (predictions.length === 0) return null;

  return (
    <Box>
      {runningPredictions.length > 0 && (
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 2,
            color: "text.secondary",
            mb: 3,
          }}
        >
          <CircularProgress size={16} />
          <Typography variant="body2">
            {t("prediction:label.predictionInProgress")}
          </Typography>
        </Box>
      )}

      {!loading && finishedPredictions.length > 0 && (
        <DatasetTable
          fetchPage={fetchPage}
          initialPageSize={5}
          deps={[allRows.length]}
          columnTypes={extendedColumnTypes}
          showExportButton={false}
          rowActions={rowActions}
        />
      )}

      <DeleteConfirmationModal
        open={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDeleteConfirm}
        content={t("prediction:label.confirmDeletion")}
      />
    </Box>
  );
}

ManualPredictionsTable.propTypes = {
  predictions: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      status: PropTypes.number.isRequired,
      created: PropTypes.string,
      results_path: PropTypes.string,
    }),
  ).isRequired,
  displayNumbers: PropTypes.instanceOf(Map).isRequired,
  targetColumn: PropTypes.string,
  datasetSample: PropTypes.object,
  onDelete: PropTypes.func,
};
