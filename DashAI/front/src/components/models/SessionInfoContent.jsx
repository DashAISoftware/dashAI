import React from "react";
import PropTypes from "prop-types";
import {
  Box,
  Typography,
  Chip,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableRow,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import { formatDate } from "../../utils";

const SPLIT_TYPE_LABEL_KEYS = {
  random: "experiments:label.random",
  manual: "experiments:label.manual",
  predefined: "experiments:label.predefined",
};

function InfoTable({ rows }) {
  return (
    <TableContainer component={Paper} sx={{ bgcolor: "rgba(0,0,0,0.2)" }}>
      <Table size="small">
        <TableBody>
          {rows.map(({ label, value }) => (
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
  );
}

InfoTable.propTypes = {
  rows: PropTypes.arrayOf(
    PropTypes.shape({ label: PropTypes.node, value: PropTypes.node }),
  ).isRequired,
};

/**
 * Shared body for a session's info: task, description, metadata (id,
 * dataset, dates) and the configuration it was created with (input/output
 * columns, split setup). Used both by InfoSessionModal (a dialog) and the
 * model detail view's right sidebar (RunInfoSidebar's "Session" tab).
 */
export default function SessionInfoContent({
  session,
  datasets = [],
  tasks = [],
}) {
  const { t } = useTranslation(["common", "experiments", "models"]);

  if (!session) return null;

  const getDatasetName = () => {
    if (!session.dataset_id || !datasets.length) return t("common:unknown");
    const dataset = datasets.find((d) => d.id === session.dataset_id);
    return dataset ? dataset.name : t("common:datasetNotFound");
  };

  const getTaskDisplayName = () => {
    if (!session.task_name) return t("common:unknown");
    const task = tasks.find((tk) => tk.name === session.task_name);
    return (
      task?.metadata?.display_name ||
      session.task_name
        .replace("Task", "")
        .replace(/([A-Z])/g, " $1")
        .trim()
    );
  };

  const metadataRows = [
    { label: t("common:id"), value: session.id },
    { label: t("common:associatedDataset"), value: getDatasetName() },
    { label: t("common:createdAt"), value: formatDate(session.created) },
    {
      label: t("common:lastModified"),
      value: formatDate(session.last_modified),
    },
  ];

  let splits = null;
  try {
    splits =
      typeof session.splits === "string"
        ? JSON.parse(session.splits)
        : session.splits;
  } catch {
    splits = null;
  }

  const yesNo = (value) => t(value ? "common:yes" : "common:no");

  const configRows = [
    {
      label: t("models:label.inputColumns"),
      value: (session.input_columns || []).join(", "),
    },
    {
      label: t("models:label.outputColumns"),
      value: (session.output_columns || []).join(", "),
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

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <Box>
        <Chip
          label={getTaskDisplayName()}
          color="primary"
          size="small"
          sx={{ mb: 2 }}
        />
        {session.description && session.description.trim() && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 2 }}>
              {t("common:description")}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {session.description}
            </Typography>
          </Box>
        )}
      </Box>

      <Box>
        <Typography variant="subtitle2" gutterBottom>
          {t("common:metadata")}
        </Typography>
        <InfoTable rows={metadataRows} />
      </Box>

      <Box>
        <Typography variant="subtitle2" gutterBottom>
          {t("models:label.configuration")}
        </Typography>
        <InfoTable rows={configRows} />
      </Box>
    </Box>
  );
}

SessionInfoContent.propTypes = {
  session: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    dataset_id: PropTypes.number,
    task_name: PropTypes.string,
    input_columns: PropTypes.array,
    output_columns: PropTypes.array,
    splits: PropTypes.oneOfType([PropTypes.string, PropTypes.object]),
    created: PropTypes.string,
    last_modified: PropTypes.string,
    description: PropTypes.string,
  }),
  datasets: PropTypes.array,
  tasks: PropTypes.array,
};
