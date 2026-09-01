import { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import { Box, IconButton, Paper, Tooltip, Typography } from "@mui/material";
import {
  MaterialReactTable,
  useMaterialReactTable,
} from "material-react-table";
import DeleteIcon from "@mui/icons-material/Delete";
import Transform from "@mui/icons-material/Transform";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import DatasetTable from "../../notebooks/dataset/DatasetTable";
import DeleteConfirmationModal from "../../threeSectionLayout/DeleteConfirmationModal";
import ItemsToDeleteList from "../../notebooks/converter/ItemsToDeleteList";
import RunStatusDot from "../../shared/RunStatusDot";
import { getConverterStatus } from "../../../utils/converterStatus";
import { useTableLocalization } from "../../../utils/useTableLocalization";
import { getCurrentDataFilePath } from "../../../utils/sessionPreprocessing";
import { getDatasetFileFiltered } from "../../../api/datasets";
import { getComponentById } from "../../../api/component";

// A card only ever renders once its converter is genuinely part of
// `session.converters` — that only happens after SessionPreprocessingJob
// reports FINISHED (see FormSessionConverterSection's onFinished/onApplied),
// never while still applying. So unlike the notebook's per-item async
// status, every session converter card is always in the finished state.
const FINISHED_STATUS = 3;

/**
 * Mirrors the notebook's own ConverterParametersTable (same columns, same
 * MaterialReactTable setup), sourced from the session converter's own
 * shape (`columns`/`target_column`) instead of the notebook's
 * (`parameters.scope.columns`/`parameters.scope.rows`/`parameters.target`).
 * No "Alcance - Filas" row: session converters have no row-level scope
 * (see ScopeStepSessionConverter.jsx).
 */
function SessionConverterParametersTable({ converter, t, localization }) {
  const paramColumns = [
    { accessorKey: "key", header: t("common:parameter"), grow: 1 },
    { accessorKey: "value", header: t("common:value"), grow: 4 },
  ];

  const paramRows = [
    {
      key: t("datasets:label.targetColumn"),
      value: converter.target_column || "",
    },
    {
      key: t("datasets:label.scopeColumns"),
      value:
        converter.columns.length === 0
          ? t("common:all")
          : converter.columns.join(", "),
    },
  ];

  const table = useMaterialReactTable({
    columns: paramColumns,
    data: paramRows,
    muiTableBodyCellProps: { sx: { whiteSpace: "pre" } },
    localization,
    initialState: { density: "compact" },
    enablePagination: false,
    enableTopToolbar: false,
    enableBottomToolbar: false,
    enableColumnActions: false,
    enableSorting: false,
    enableColumnFilter: false,
    muiTablePaperProps: { elevation: 0 },
  });

  return <MaterialReactTable table={table} />;
}

/**
 * A single applied-converter card. Styled after the notebook's own
 * ConverterBox (icon + status dot + real component display name +
 * description + parameters table) but built against the session's
 * converter shape (`{converter, params, columns, target_column}`) instead
 * of the notebook's (`{parameters: {scope: {columns, rows}, target}}`) —
 * reusing ConverterBox directly left empty sections since those fields
 * don't exist here, and there's no per-item async status to poll for (see
 * FINISHED_STATUS above).
 */
function SessionConverterCard({ converter, disabled, onDelete }) {
  const theme = useTheme();
  const { t } = useTranslation(["common", "datasets"]);
  const localization = useTableLocalization();
  const [component, setComponent] = useState(null);

  useEffect(() => {
    let cancelled = false;
    getComponentById(converter.converter)
      .then((data) => {
        if (!cancelled) setComponent(data);
      })
      .catch((error) => {
        console.error("Failed to fetch converter component:", error);
      });
    return () => {
      cancelled = true;
    };
  }, [converter.converter]);

  return (
    <Paper
      variant="outlined"
      sx={{
        p: 4,
        bgcolor: "background.paper",
        borderColor: theme.palette.ui.border,
        borderRadius: 1,
      }}
    >
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 3,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <Transform sx={{ color: theme.palette.primary.main, fontSize: 20 }} />
          <Typography variant="subtitle2">
            {component?.display_name || converter.converter}
          </Typography>
          <Tooltip title={getConverterStatus(FINISHED_STATUS, t)}>
            <span>
              <RunStatusDot status={FINISHED_STATUS} />
            </span>
          </Tooltip>
        </Box>
        <IconButton
          size="small"
          color="error"
          disabled={disabled}
          onClick={onDelete}
          aria-label={t("common:remove")}
        >
          <DeleteIcon fontSize="small" />
        </IconButton>
      </Box>
      <Box
        sx={{
          bgcolor: theme.palette.background.default,
          borderRadius: 1,
          p: 3,
        }}
      >
        {component?.description && (
          <Typography variant="body2" sx={{ color: "text.secondary", mb: 3 }}>
            {component.description}
          </Typography>
        )}
        <SessionConverterParametersTable
          converter={converter}
          t={t}
          localization={localization}
        />
      </Box>
    </Paper>
  );
}

/**
 * Center-panel content for the session wizard's preprocessing step: a live
 * preview of the session's *current* data (the raw dataset, or the latest
 * applied-converters partition once one exists — see
 * getCurrentDataFilePath) plus a card per entry already in
 * `session.converters`, each removable. Mirrors the notebook feature's own
 * dataset-preview + tool-card pattern; adding a converter happens from the
 * sidebar (SessionConvertersRightBar), this component only renders what's
 * already applied and lets the user remove one.
 *
 * Removing a converter cascades to every converter applied after it (a
 * later converter may have been scoped against columns this one produced),
 * matching the notebook's own converter deletion — confirmed first via the
 * same `DeleteConfirmationModal` + `ItemsToDeleteList` notebooks use, so
 * the user sees exactly what else is about to go.
 *
 * `columnTypes` is the session's *current* column types, which
 * PreprocessingStep already re-fetches (from
 * `GET /model-session/{id}/preprocessed-columns`) alongside the session
 * itself for the sidebar's scoping logic — so it describes the same file
 * this table is previewing. Reused here rather than re-fetched, matching
 * ConfigureToolModal's own precedent of previewing this file path with that
 * same shared columnTypes, instead of rendering the table with no type
 * information at all.
 */
export default function AppliedConvertersView({
  session,
  isApplying,
  onRemoveConverter,
  columnTypes = {},
}) {
  const { t } = useTranslation(["models", "datasets", "common"]);
  const filePath = getCurrentDataFilePath(session);
  const converters = session.converters || [];
  const [deleteIndex, setDeleteIndex] = useState(null);

  const fetchDatasetPage = (page, pageSize, filterModel, sortModel) =>
    getDatasetFileFiltered(filePath, page, pageSize, filterModel, sortModel);

  const itemsToDelete = useMemo(() => {
    if (deleteIndex === null) return [];
    return converters.slice(deleteIndex).map((converter, i) => ({
      id: deleteIndex + i,
      type: "converter",
      converter: converter.converter,
    }));
  }, [converters, deleteIndex]);

  const handleConfirmDelete = () => {
    onRemoveConverter(deleteIndex);
    setDeleteIndex(null);
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <Box sx={{ position: "relative" }}>
        <DatasetTable
          fetchPage={fetchDatasetPage}
          // `filePath` alone is NOT enough to detect a change: once a session
          // has a `preprocessed_path`, that path is a stable per-session
          // directory the backend rewrites *in place* on every apply/remove,
          // so it's byte-identical before and after the 2nd, 3rd... converter
          // and the table would never refetch. `last_modified` is bumped by
          // the DB on every write to the session row (converters replaced,
          // preprocessing status advancing to FINISHED/ERROR), so it changes
          // exactly when the underlying data does.
          deps={[filePath, session.last_modified]}
          initialPageSize={5}
          datasetPath={filePath}
          columnTypes={columnTypes}
          enableTopToolbar={false}
          enableRowsPerPageSelector={false}
        />
      </Box>
      <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {converters.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            {t("models:label.noConvertersAdded")}
          </Typography>
        ) : (
          converters.map((converter, index) => (
            <SessionConverterCard
              key={`${converter.converter}-${index}`}
              converter={converter}
              disabled={isApplying}
              onDelete={() => setDeleteIndex(index)}
            />
          ))
        )}
      </Box>

      <DeleteConfirmationModal
        open={deleteIndex !== null}
        onClose={() => setDeleteIndex(null)}
        onConfirm={handleConfirmDelete}
        content={
          <Box>
            <Typography>
              {t("models:label.deleteConverterConfirmation", {
                converter: converters[deleteIndex]?.converter,
              })}
            </Typography>
            <ItemsToDeleteList items={itemsToDelete} />
          </Box>
        }
      />
    </Box>
  );
}

SessionConverterCard.propTypes = {
  converter: PropTypes.shape({
    converter: PropTypes.string.isRequired,
    columns: PropTypes.arrayOf(PropTypes.string).isRequired,
    target_column: PropTypes.string,
  }).isRequired,
  disabled: PropTypes.bool,
  onDelete: PropTypes.func.isRequired,
};

AppliedConvertersView.propTypes = {
  session: PropTypes.object.isRequired,
  isApplying: PropTypes.bool.isRequired,
  onRemoveConverter: PropTypes.func.isRequired,
  columnTypes: PropTypes.object,
};
