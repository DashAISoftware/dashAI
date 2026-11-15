import {
  Alert,
  Box,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import StepperNavigationFooter from "../shared/StepperNavigationFooter";
import ExportBreadcrumbs from "./ExportBreadcrumbs";

/**
 * Third step of the dataset export flow: describe the dataset.
 *
 * The form lives in the right panel; this center view previews the dataset
 * and marks which columns are the target, which are ignored and which the
 * platform cannot store.
 *
 * @param {string} platformName - Display name of the chosen platform.
 * @param {string} datasetName - Name of the dataset being exported.
 * @param {Array<string>} columns - All dataset columns, in order.
 * @param {object} sample - Preview rows as ``{column: [values]}``.
 * @param {Array<string>} unsupportedColumns - Columns the platform cannot store.
 * @param {string} target - Selected target column ("" when none).
 * @param {Array<string>} ignored - Selected ignored columns.
 * @param {boolean} loading - Whether the dataset is still loading.
 * @param {boolean} error - Whether the dataset failed to load.
 * @param {boolean} canContinue - Whether the form is complete and valid.
 * @param {function} onPlatformClick - Returns to the dataset list.
 * @param {function} onBack - Returns to the dataset list.
 * @param {function} onNext - Continues to the review step.
 */
export default function ExportMetadataStep({
  platformName,
  datasetName,
  columns,
  sample,
  unsupportedColumns,
  target,
  ignored,
  loading,
  error,
  canContinue,
  onPlatformClick,
  onBack,
  onNext,
}) {
  const { t } = useTranslation(["export"]);
  const rowCount = Math.max(
    0,
    ...columns.map((column) => sample?.[column]?.length ?? 0),
  );

  const columnRole = (column) => {
    if (unsupportedColumns.includes(column)) return "unsupported";
    if (column === target) return "target";
    if (ignored.includes(column)) return "ignored";
    return null;
  };

  const headerSx = {
    target: { color: "primary.main", fontWeight: 600 },
    ignored: { color: "text.disabled" },
    unsupported: { color: "text.disabled", textDecoration: "line-through" },
  };

  const renderPreview = () => {
    if (loading) {
      return (
        <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
          <CircularProgress size={28} />
        </Box>
      );
    }
    if (error) {
      return <Alert severity="error">{t("export:datasetLoadError")}</Alert>;
    }
    return (
      <TableContainer
        sx={{ border: 1, borderColor: "divider", borderRadius: 1 }}
      >
        <Table size="small" aria-label={t("export:previewLabel")}>
          <TableHead>
            <TableRow>
              {columns.map((column) => {
                const role = columnRole(column);
                return (
                  <TableCell
                    key={column}
                    sx={{
                      whiteSpace: "nowrap",
                      ...(role ? headerSx[role] : {}),
                      ...(role === "target"
                        ? { backgroundColor: "action.selected" }
                        : {}),
                    }}
                  >
                    {column}
                    {role && (
                      <Typography
                        component="span"
                        variant="caption"
                        sx={{ display: "block", textDecoration: "none" }}
                      >
                        {t(`export:role.${role}`)}
                      </Typography>
                    )}
                  </TableCell>
                );
              })}
            </TableRow>
          </TableHead>
          <TableBody>
            {Array.from({ length: rowCount }, (_, rowIndex) => (
              <TableRow key={rowIndex}>
                {columns.map((column) => {
                  const role = columnRole(column);
                  const value = sample?.[column]?.[rowIndex];
                  return (
                    <TableCell
                      key={column}
                      sx={{
                        whiteSpace: "nowrap",
                        color:
                          role === "ignored" || role === "unsupported"
                            ? "text.disabled"
                            : undefined,
                        ...(role === "target"
                          ? { backgroundColor: "action.hover" }
                          : {}),
                      }}
                    >
                      {role === "unsupported" ? "—" : String(value ?? "")}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    );
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        width: "100%",
        height: "100%",
        px: 4,
        pt: 4,
      }}
    >
      <ExportBreadcrumbs
        crumbs={[
          { label: platformName, onClick: onPlatformClick },
          { label: datasetName },
        ]}
        onBack={onBack}
      />
      <Box sx={{ mb: 2 }}>
        <Typography variant="h5" component="h1">
          {t("export:metadataTitle", { platform: platformName })}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {t("export:metadataSubtitle")}
        </Typography>
      </Box>
      <Box sx={{ flex: 1, minHeight: 0, overflow: "auto", pb: 2 }}>
        {renderPreview()}
        {!loading && !error && unsupportedColumns.length > 0 && (
          <Alert severity="warning" sx={{ mt: 2 }}>
            {t("export:columnsLeftOut", {
              columns: unsupportedColumns.join(", "),
            })}
          </Alert>
        )}
      </Box>
      {!canContinue && !loading && !error && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          {t("export:metadataIncomplete")}
        </Typography>
      )}
      <StepperNavigationFooter
        onBack={onBack}
        onNext={onNext}
        nextDisabled={!canContinue}
        nextLabel={t("export:review")}
      />
    </Box>
  );
}

ExportMetadataStep.propTypes = {
  platformName: PropTypes.string.isRequired,
  datasetName: PropTypes.string.isRequired,
  columns: PropTypes.arrayOf(PropTypes.string).isRequired,
  sample: PropTypes.object,
  unsupportedColumns: PropTypes.arrayOf(PropTypes.string).isRequired,
  target: PropTypes.string.isRequired,
  ignored: PropTypes.arrayOf(PropTypes.string).isRequired,
  loading: PropTypes.bool,
  error: PropTypes.bool,
  canContinue: PropTypes.bool,
  onPlatformClick: PropTypes.func.isRequired,
  onBack: PropTypes.func.isRequired,
  onNext: PropTypes.func.isRequired,
};
