import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { formatDate } from "../../utils";
import { useTranslation } from "react-i18next";
import InfoModal from "../shared/InfoModal";

export default function InfoSessionModal({
  sessionData,
  datasets = [],
  tasks = [],
  open,
  onClose,
}) {
  const { t } = useTranslation(["common"]);

  // Find the associated dataset name
  const getDatasetName = () => {
    if (!sessionData.dataset_id || !datasets.length) {
      return t("common:unknown");
    }
    const dataset = datasets.find((d) => d.id === sessionData.dataset_id);
    return dataset ? dataset.name : t("common:datasetNotFound");
  };

  // Get task display name
  const getTaskDisplayName = () => {
    if (!sessionData.task_name) return t("common:unknown");
    const task = tasks.find((t) => t.name === sessionData.task_name);
    return (
      task?.metadata?.display_name ||
      sessionData.task_name
        .replace("Task", "")
        .replace(/([A-Z])/g, " $1")
        .trim()
    );
  };

  // If no session data is provided, don't render anything
  if (!sessionData) return null;

  const rows = [
    { label: t("common:id"), value: sessionData.id },
    { label: t("common:task"), value: getTaskDisplayName() },
    { label: t("common:associatedDataset"), value: getDatasetName() },
    { label: t("common:createdAt"), value: formatDate(sessionData.created) },
    {
      label: t("common:lastModified"),
      value: formatDate(sessionData.last_modified),
    },
  ];

  const extraContent = sessionData.description &&
    sessionData.description.trim() && (
      <Box sx={{ mb: 6 }}>
        <Typography variant="subtitle2" sx={{ mb: 2 }}>
          {t("common:description")}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
          {sessionData.description}
        </Typography>
      </Box>
    );

  return (
    <InfoModal
      title={t("common:sessionInformation")}
      subtitle={sessionData.name}
      rows={rows}
      extraContent={extraContent}
      open={open}
      onClose={onClose}
    />
  );
}
