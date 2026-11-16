import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Link,
  Paper,
  Step,
  StepLabel,
  Stepper,
  Typography,
} from "@mui/material";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import ExportBreadcrumbs from "./ExportBreadcrumbs";

/** Export status mapped to the number of finished phases. */
const COMPLETED_PHASES = {
  pending: 0,
  preparing: 0,
  uploading: 1,
  published: 3,
};
const PHASES = ["preparing", "uploading", "published"];

/**
 * Last step of the dataset export flow: follow the publication.
 *
 * Shows the phase the export job is in, then the link to the published
 * dataset or the reason it failed. The job runs in the background, so the
 * user can leave this page at any time.
 *
 * @param {object|null} exportRow - The export record from the API.
 * @param {string} platformName - Display name of the export platform.
 * @param {boolean} loading - Whether the export record is still loading.
 * @param {boolean} notFound - Whether the export does not exist.
 * @param {function} onPlatformClick - Opens the platform's dataset list.
 * @param {function} onDatasetClick - Opens the exported dataset.
 * @param {function} onRetry - Goes back to the review with the same metadata.
 */
export default function ExportProgressStep({
  exportRow,
  platformName,
  loading,
  notFound,
  onPlatformClick,
  onDatasetClick,
  onRetry,
}) {
  const { t } = useTranslation(["export"]);
  const status = exportRow?.status;
  const inProgress = status && !["published", "error"].includes(status);

  const title = () => {
    if (status === "published") {
      return t("export:publishedTitle", { platform: platformName });
    }
    if (status === "error") {
      return t("export:failedTitle", { platform: platformName });
    }
    return t("export:publishingTitle", { platform: platformName });
  };

  const renderBody = () => {
    if (loading && !exportRow) {
      return (
        <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
          <CircularProgress size={28} />
        </Box>
      );
    }
    if (notFound || !exportRow) {
      return <Alert severity="error">{t("export:exportNotFound")}</Alert>;
    }
    return (
      <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
        {status !== "error" && (
          <Stepper activeStep={COMPLETED_PHASES[status] ?? 0} alternativeLabel>
            {PHASES.map((phase) => (
              <Step key={phase}>
                <StepLabel>{t(`export:phase.${phase}`)}</StepLabel>
              </Step>
            ))}
          </Stepper>
        )}

        {inProgress && (
          <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
            <CircularProgress size={18} />
            <Typography variant="body2">
              {t(`export:phaseDetail.${status}`, { platform: platformName })}
            </Typography>
          </Box>
        )}

        {status === "published" && (
          <Paper variant="outlined" sx={{ p: 3 }}>
            <Typography variant="subtitle1" fontWeight={600}>
              {t("export:publishedId", {
                name: exportRow.dataset_name,
                id: exportRow.remote_id,
              })}
            </Typography>
            {exportRow.remote_url && (
              <Link
                href={exportRow.remote_url}
                target="_blank"
                rel="noopener noreferrer"
                sx={{ wordBreak: "break-all" }}
              >
                {exportRow.remote_url}
              </Link>
            )}
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              {t("export:publishedNote", { platform: platformName })}
            </Typography>
          </Paper>
        )}

        {status === "error" && (
          <Alert severity="error">
            <Typography variant="body2" fontWeight={600}>
              {t("export:failedReason")}
            </Typography>
            <Typography variant="body2" sx={{ wordBreak: "break-word" }}>
              {exportRow.error_message}
            </Typography>
          </Alert>
        )}
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
          ...(exportRow
            ? [{ label: exportRow.dataset_name, onClick: onDatasetClick }]
            : []),
          { label: t("export:statusCrumb") },
        ]}
        onBack={onPlatformClick}
      />
      <Box sx={{ mb: 2 }}>
        <Typography variant="h5" component="h1">
          {title()}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {t("export:progressSubtitle")}
        </Typography>
      </Box>
      <Box sx={{ flex: 1, minHeight: 0, overflow: "auto", pb: 2 }}>
        {renderBody()}
      </Box>
      <Box
        sx={{
          display: "flex",
          justifyContent: "flex-end",
          gap: 2,
          py: 3,
          borderTop: 1,
          borderColor: "divider",
        }}
      >
        {exportRow?.dataset_id && (
          <Button variant="outlined" onClick={onDatasetClick}>
            {t("export:backToDataset")}
          </Button>
        )}
        {status === "error" && exportRow?.dataset_id && (
          <Button variant="contained" onClick={onRetry}>
            {t("export:retry")}
          </Button>
        )}
        {status === "published" && exportRow.remote_url && (
          <Button
            variant="contained"
            href={exportRow.remote_url}
            target="_blank"
            rel="noopener noreferrer"
            endIcon={<OpenInNewIcon />}
          >
            {t("export:viewOn", { platform: platformName })}
          </Button>
        )}
      </Box>
    </Box>
  );
}

ExportProgressStep.propTypes = {
  exportRow: PropTypes.shape({
    status: PropTypes.string.isRequired,
    dataset_id: PropTypes.number,
    dataset_name: PropTypes.string.isRequired,
    remote_id: PropTypes.string,
    remote_url: PropTypes.string,
    error_message: PropTypes.string,
  }),
  platformName: PropTypes.string.isRequired,
  loading: PropTypes.bool,
  notFound: PropTypes.bool,
  onPlatformClick: PropTypes.func.isRequired,
  onDatasetClick: PropTypes.func.isRequired,
  onRetry: PropTypes.func.isRequired,
};
