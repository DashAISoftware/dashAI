import React, { useCallback, useEffect, useState } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  IconButton,
  Tooltip,
  Typography,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import DeleteIcon from "@mui/icons-material/Delete";
import { useTranslation } from "react-i18next";

import { getReportArtifacts } from "../../api/report";
import ArtifactList from "../shared/ArtifactList";

/** Status codes shared with the backend ReportStatus enum. */
const STATUS = {
  NOT_STARTED: 0,
  DELIVERED: 1,
  STARTED: 2,
  FINISHED: 3,
  ERROR: 4,
};

/** How often an unfinished report re-reads its artifacts. */
const POLL_INTERVAL_MS = 3000;

/**
 * One computed report: its name, the split it describes, and its
 * artifacts. Polls only while the job is outstanding, so a settled card makes
 * no requests.
 */
export default function ReportCard({ report, displayName, onDelete }) {
  const theme = useTheme();
  const { t } = useTranslation(["reports", "common"]);
  const [artifacts, setArtifacts] = useState([]);
  const [loading, setLoading] = useState(report.status === STATUS.FINISHED);
  const [status, setStatus] = useState(report.status);

  const fetchArtifacts = useCallback(async () => {
    try {
      const response = await getReportArtifacts(report.id);
      setArtifacts(response ?? []);
    } catch (error) {
      console.error("Error fetching report artifacts:", error);
    }
  }, [report.id]);

  useEffect(() => {
    setStatus(report.status);
  }, [report.status]);

  useEffect(() => {
    if (status !== STATUS.FINISHED) return;
    setLoading(true);
    fetchArtifacts().finally(() => setLoading(false));
  }, [status, fetchArtifacts]);

  const running = status === STATUS.DELIVERED || status === STATUS.STARTED;

  // The parent list refreshes rows on its own trigger; this keeps a single
  // running card honest between those refreshes without a global poll.
  useEffect(() => {
    if (!running) return undefined;
    const handle = setInterval(fetchArtifacts, POLL_INTERVAL_MS);
    return () => clearInterval(handle);
  }, [running, fetchArtifacts]);

  return (
    <Card
      elevation={0}
      sx={{
        border: `1px solid ${theme.palette.ui.border}`,
        bgcolor: theme.palette.ui.box,
      }}
    >
      <CardContent>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 2,
            mb: 2,
          }}
        >
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            {displayName || report.report_name}
          </Typography>
          <Chip size="small" label={t(`reports:label.split_${report.split}`)} />
          <Box sx={{ flex: 1 }} />
          <Tooltip title={t("reports:button.delete")}>
            <IconButton
              size="small"
              color="error"
              onClick={() => onDelete(report)}
            >
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>

        {status === STATUS.ERROR ? (
          <Typography variant="body2" color="error">
            {t("reports:message.failed")}
          </Typography>
        ) : running || loading ? (
          <Box sx={{ display: "flex", alignItems: "center", gap: 2, py: 2 }}>
            <CircularProgress size={18} />
            <Typography variant="body2" color="text.secondary">
              {t("reports:message.computing")}
            </Typography>
          </Box>
        ) : artifacts.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            {t("reports:message.noData")}
          </Typography>
        ) : (
          <ArtifactList items={artifacts} />
        )}
      </CardContent>
    </Card>
  );
}

ReportCard.propTypes = {
  report: PropTypes.shape({
    id: PropTypes.number.isRequired,
    report_name: PropTypes.string,
    split: PropTypes.string,
    status: PropTypes.number,
  }).isRequired,
  displayName: PropTypes.string,
  onDelete: PropTypes.func.isRequired,
};
