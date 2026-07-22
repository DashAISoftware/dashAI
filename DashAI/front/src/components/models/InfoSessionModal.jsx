import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableRow from "@mui/material/TableRow";
import { formatDate } from "../../utils";
import { useTranslation } from "react-i18next";
import InfoModal from "../shared/InfoModal";

const SPLIT_TYPE_LABEL_KEYS = {
  random: "experiments:label.random",
  manual: "experiments:label.manual",
  predefined: "experiments:label.predefined",
};

export default function InfoSessionModal({
  sessionData,
  datasets = [],
  tasks = [],
  open,
  onClose,
}) {
  const { t } = useTranslation(["common", "experiments", "models"]);

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
    { label: t("common:associatedDataset"), value: getDatasetName() },
    { label: t("common:createdAt"), value: formatDate(sessionData.created) },
    {
      label: t("common:lastModified"),
      value: formatDate(sessionData.last_modified),
    },
  ];

  let splits = null;
  try {
    splits =
      typeof sessionData.splits === "string"
        ? JSON.parse(sessionData.splits)
        : sessionData.splits;
  } catch {
    splits = null;
  }

  const yesNo = (value) => t(value ? "common:yes" : "common:no");

  const configRows = [
    {
      label: t("models:label.inputColumns"),
      value: (sessionData.input_columns || []).join(", "),
    },
    {
      label: t("models:label.outputColumns"),
      value: (sessionData.output_columns || []).join(", "),
    },
  ];

  if (splits?.splitType) {
    configRows.push({
      label: t("experiments:label.splitType"),
      value: t(SPLIT_TYPE_LABEL_KEYS[splits.splitType] || splits.splitType),
    });

    if (splits.splitType === "random") {
      configRows.push(
        { label: t("common:train"), value: splits.train },
        { label: t("common:validation"), value: splits.validation },
        { label: t("common:test"), value: splits.test },
        { label: t("experiments:label.shuffle"), value: yesNo(splits.shuffle) },
        {
          label: t("experiments:label.stratify"),
          value: yesNo(splits.stratify),
        },
        { label: t("experiments:label.seed"), value: splits.seed },
      );
    } else {
      configRows.push(
        { label: t("common:train"), value: (splits.train || []).length },
        {
          label: t("common:validation"),
          value: (splits.validation || []).length,
        },
        { label: t("common:test"), value: (splits.test || []).length },
      );
    }
  }

  const extraContent = (
    <>
      <Chip
        label={getTaskDisplayName()}
        color="primary"
        size="small"
        sx={{ mb: 2 }}
      />

      {sessionData.description && sessionData.description.trim() && (
        <Box sx={{ mb: 6 }}>
          <Typography variant="subtitle2" sx={{ mb: 2 }}>
            {t("common:description")}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
            {sessionData.description}
          </Typography>
        </Box>
      )}

      <Typography variant="subtitle2" sx={{ mb: 2 }}>
        {t("models:label.configuration")}
      </Typography>
      <TableContainer
        component={Paper}
        sx={{ mb: 6, bgcolor: "rgba(0,0,0,0.2)" }}
      >
        <Table size="small">
          <TableBody>
            {configRows.map(({ label, value }) => (
              <TableRow key={label}>
                <TableCell
                  component="th"
                  scope="row"
                  sx={{ color: "text.secondary" }}
                >
                  {label}
                </TableCell>
                <TableCell align="right">{value}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </>
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
