import PropTypes from "prop-types";
import {
  Box,
  Card,
  CardContent,
  CardHeader,
  CircularProgress,
  IconButton,
  Typography,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import DatasetTable from "../../notebooks/dataset/DatasetTable";
import { getCurrentDataFilePath } from "../../../utils/sessionPreprocessing";
import { getDatasetFileFiltered } from "../../../api/datasets";

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
  const theme = useTheme();
  const { t } = useTranslation(["models", "datasets", "common"]);
  const filePath = getCurrentDataFilePath(session);
  const converters = session.converters || [];

  const fetchDatasetPage = (page, pageSize, filterModel, sortModel) =>
    getDatasetFileFiltered(filePath, page, pageSize, filterModel, sortModel);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <Box sx={{ position: "relative" }}>
        {isApplying && (
          <Box
            sx={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              bgcolor: "rgba(0,0,0,0.4)",
              zIndex: 1,
            }}
          >
            <CircularProgress />
          </Box>
        )}
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
            <Card
              key={`${converter.converter}-${index}`}
              variant="outlined"
              sx={{ borderColor: theme.palette.ui.border }}
            >
              <CardHeader
                title={converter.converter}
                slotProps={{ title: { variant: "subtitle2" } }}
                action={
                  <IconButton
                    size="small"
                    color="error"
                    disabled={isApplying}
                    onClick={() => onRemoveConverter(index)}
                    aria-label={t("common:remove")}
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                }
              />
              <CardContent sx={{ pt: 0 }}>
                <Typography variant="body2" color="text.secondary">
                  {t("models:label.converterColumns", {
                    columns: converter.columns.join(", "),
                  })}
                </Typography>
                {converter.target_column && (
                  <Typography variant="body2" color="text.secondary">
                    {t("datasets:label.targetColumn")}:{" "}
                    {converter.target_column}
                  </Typography>
                )}
              </CardContent>
            </Card>
          ))
        )}
      </Box>
    </Box>
  );
}

AppliedConvertersView.propTypes = {
  session: PropTypes.object.isRequired,
  isApplying: PropTypes.bool.isRequired,
  onRemoveConverter: PropTypes.func.isRequired,
  columnTypes: PropTypes.object,
};
