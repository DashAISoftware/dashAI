import { Box, Typography } from "@mui/material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import ComponentSelector from "../custom/ComponentSelector";
import StepperNavigationFooter from "../shared/StepperNavigationFooter";
import ExportBreadcrumbs from "./ExportBreadcrumbs";
import {
  getComponentCredentialState,
  useCredentialStatuses,
} from "../credentials/credentialStatus";

/**
 * First step of the dataset export flow: choose the target platform.
 *
 * Lists the registered DatasetExporter components. A platform whose required
 * credential is missing can still be selected (to read its details), but the
 * flow only continues once the credential is added from the card's key icon.
 *
 * @param {Array<object>} exporters - DatasetExporter components from the registry.
 * @param {object|null} selected - The exporter currently selected.
 * @param {function} onSelect - Called with the clicked exporter.
 * @param {function} onBack - Leaves the export flow.
 * @param {function} onNext - Continues with the selected exporter.
 */
export default function ExportPlatformStep({
  exporters,
  selected,
  onSelect,
  onBack,
  onNext,
}) {
  const { t } = useTranslation(["export"]);
  const { statuses, loaded } = useCredentialStatuses();
  const { locked, requiredPlatforms } = getComponentCredentialState(
    selected,
    statuses,
    loaded,
  );

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
      <ExportBreadcrumbs onBack={onBack} />
      <Box sx={{ mb: 2 }}>
        <Typography variant="h5" component="h1">
          {t("export:selectPlatformTitle")}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {t("export:selectPlatformSubtitle")}
        </Typography>
      </Box>
      <Box sx={{ flex: 1, minHeight: 0, pb: 4 }}>
        <ComponentSelector
          components={exporters.map((exporter) => ({
            ...exporter,
            category: exporter.metadata?.category,
          }))}
          selected={selected}
          onSelect={onSelect}
          searchPlaceholder={t("export:searchPlatforms")}
          emptyText={t("export:noPlatforms")}
        />
      </Box>
      {selected && locked && (
        <Typography variant="body2" color="warning.main" sx={{ mb: 1 }}>
          {t("export:credentialRequired", { platform: requiredPlatforms })}
        </Typography>
      )}
      <StepperNavigationFooter
        onBack={onBack}
        onNext={() => onNext(selected)}
        nextDisabled={!selected || locked}
      />
    </Box>
  );
}

ExportPlatformStep.propTypes = {
  exporters: PropTypes.arrayOf(
    PropTypes.shape({ name: PropTypes.string.isRequired }),
  ).isRequired,
  selected: PropTypes.shape({ name: PropTypes.string }),
  onSelect: PropTypes.func.isRequired,
  onBack: PropTypes.func.isRequired,
  onNext: PropTypes.func.isRequired,
};
