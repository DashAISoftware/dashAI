import {
  Alert,
  Box,
  Button,
  Checkbox,
  CircularProgress,
  FormControlLabel,
  Paper,
  Typography,
} from "@mui/material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import StepperNavigationFooter from "../shared/StepperNavigationFooter";
import ExportBreadcrumbs from "./ExportBreadcrumbs";

/** Format a parameter value for the summary; null when it was left empty. */
const formatValue = (value) => {
  if (value === null || value === undefined) return null;
  if (Array.isArray(value)) return value.length ? value.join(", ") : null;
  const text = String(value).trim();
  return text || null;
};

/**
 * Fourth step of the dataset export flow: review and confirm.
 *
 * Shows the validation result, the metadata about to be sent and what will
 * reach the platform, and asks the user to acknowledge that publishing is
 * public before enabling the publish button.
 *
 * @param {string} platformName - Display name of the chosen platform.
 * @param {string} datasetName - Name of the dataset being exported.
 * @param {object|null} params - Export parameters from the metadata step;
 *   null when they were lost (for example, after reloading the page).
 * @param {object} fieldTitles - Schema field name mapped to its label.
 * @param {object} summary - ``{rows, columns, sentColumns, leftOut}``.
 * @param {object} validation - ``{loading, errors, warnings, failed}``;
 *   warnings describe adjustments that do not block publishing.
 * @param {boolean} confirmed - Whether the user acknowledged publishing.
 * @param {function} onConfirmChange - Called with the new acknowledgement.
 * @param {boolean} publishing - Whether the export is being created.
 * @param {string|null} publishError - Why creating the export failed.
 * @param {function} onPlatformClick - Returns to the dataset list.
 * @param {function} onBack - Returns to the metadata step.
 * @param {function} onPublish - Creates the export.
 */
export default function ExportReviewStep({
  platformName,
  datasetName,
  params,
  fieldTitles,
  summary,
  validation,
  confirmed,
  onConfirmChange,
  publishing,
  publishError,
  onPlatformClick,
  onBack,
  onPublish,
}) {
  const { t } = useTranslation(["export"]);

  const filledFields = params
    ? Object.entries(params)
        .map(([key, value]) => [key, formatValue(value)])
        .filter(([, value]) => value !== null)
    : [];

  const canPublish =
    Boolean(params) &&
    !validation.loading &&
    !validation.failed &&
    validation.errors.length === 0 &&
    confirmed &&
    !publishing;

  const renderValidation = () => {
    if (validation.loading) {
      return (
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <CircularProgress size={18} />
          <Typography variant="body2">{t("export:validating")}</Typography>
        </Box>
      );
    }
    if (validation.failed) {
      return <Alert severity="error">{t("export:validationFailed")}</Alert>;
    }
    if (validation.errors.length) {
      return (
        <Alert severity="error">
          <Typography variant="body2" fontWeight={600}>
            {t("export:validationErrors")}
          </Typography>
          <Box component="ul" sx={{ m: 0, pl: 3 }}>
            {validation.errors.map((error) => (
              <li key={error}>{error}</li>
            ))}
          </Box>
        </Alert>
      );
    }
    return (
      <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <Alert severity="success">{t("export:validationOk")}</Alert>
        {validation.warnings?.length > 0 && (
          <Alert severity="info">
            <Typography variant="body2" fontWeight={600}>
              {t("export:validationWarnings", { platform: platformName })}
            </Typography>
            <Box component="ul" sx={{ m: 0, pl: 3 }}>
              {validation.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </Box>
          </Alert>
        )}
      </Box>
    );
  };

  const renderContent = () => {
    if (!params) {
      return (
        <Alert
          severity="info"
          action={
            <Button color="inherit" size="small" onClick={onBack}>
              {t("export:backToForm")}
            </Button>
          }
        >
          {t("export:paramsLost")}
        </Alert>
      );
    }
    return (
      <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
        {renderValidation()}

        <Paper variant="outlined" sx={{ p: 3 }}>
          <Typography variant="subtitle2" sx={{ mb: 2 }}>
            {t("export:summaryMetadata")}
          </Typography>
          <Box
            component="dl"
            sx={{
              m: 0,
              display: "grid",
              gridTemplateColumns: "minmax(140px, max-content) 1fr",
              columnGap: 3,
              rowGap: 1,
            }}
          >
            {filledFields.map(([key, value]) => (
              <Box key={key} sx={{ display: "contents" }}>
                <Typography
                  component="dt"
                  variant="body2"
                  color="text.secondary"
                >
                  {fieldTitles[key] ?? key}
                </Typography>
                <Typography
                  component="dd"
                  variant="body2"
                  sx={{ m: 0, wordBreak: "break-word" }}
                >
                  {value}
                </Typography>
              </Box>
            ))}
          </Box>
        </Paper>

        <Paper variant="outlined" sx={{ p: 3 }}>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            {t("export:summarySent")}
          </Typography>
          <Typography variant="body2">
            {t("export:summaryRows", { rows: summary.rows ?? "-" })}
          </Typography>
          <Typography variant="body2">
            {t("export:summaryColumns", {
              sent: summary.sentColumns,
              total: summary.columns,
            })}
          </Typography>
          {summary.leftOut.length > 0 && (
            <Typography variant="body2" color="warning.main">
              {t("export:columnsLeftOut", {
                columns: summary.leftOut.join(", "),
              })}
            </Typography>
          )}
        </Paper>

        <Alert severity="warning">
          <Typography variant="body2" fontWeight={600}>
            {t("export:publicTitle", { platform: platformName })}
          </Typography>
          <Typography variant="body2">
            {t("export:publicBody", { platform: platformName })}
          </Typography>
          <FormControlLabel
            control={
              <Checkbox
                checked={confirmed}
                onChange={(event) => onConfirmChange(event.target.checked)}
              />
            }
            label={t("export:publicConfirm")}
          />
        </Alert>

        {publishError && <Alert severity="error">{publishError}</Alert>}
      </Box>
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
          { label: datasetName, onClick: onBack },
          { label: t("export:reviewCrumb") },
        ]}
        onBack={onBack}
      />
      <Box sx={{ mb: 2 }}>
        <Typography variant="h5" component="h1">
          {t("export:reviewTitle")}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {t("export:reviewSubtitle", { platform: platformName })}
        </Typography>
      </Box>
      <Box sx={{ flex: 1, minHeight: 0, overflow: "auto", pb: 2 }}>
        {renderContent()}
      </Box>
      <StepperNavigationFooter
        onBack={onBack}
        onNext={onPublish}
        nextDisabled={!canPublish}
        loading={publishing}
        nextLabel={t("export:publish", { platform: platformName })}
      />
    </Box>
  );
}

ExportReviewStep.propTypes = {
  platformName: PropTypes.string.isRequired,
  datasetName: PropTypes.string.isRequired,
  params: PropTypes.object,
  fieldTitles: PropTypes.objectOf(PropTypes.string).isRequired,
  summary: PropTypes.shape({
    rows: PropTypes.number,
    columns: PropTypes.number,
    sentColumns: PropTypes.number,
    leftOut: PropTypes.arrayOf(PropTypes.string).isRequired,
  }).isRequired,
  validation: PropTypes.shape({
    loading: PropTypes.bool,
    errors: PropTypes.arrayOf(PropTypes.string).isRequired,
    warnings: PropTypes.arrayOf(PropTypes.string),
    failed: PropTypes.bool,
  }).isRequired,
  confirmed: PropTypes.bool.isRequired,
  onConfirmChange: PropTypes.func.isRequired,
  publishing: PropTypes.bool,
  publishError: PropTypes.string,
  onPlatformClick: PropTypes.func.isRequired,
  onBack: PropTypes.func.isRequired,
  onPublish: PropTypes.func.isRequired,
};
