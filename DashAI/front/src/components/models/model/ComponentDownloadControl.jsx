import React, { useState, useEffect } from "react";
import { Box, Button, LinearProgress, Typography } from "@mui/material";
import DownloadIcon from "@mui/icons-material/Download";
import DeleteIcon from "@mui/icons-material/Delete";
import { useTranslation } from "react-i18next";
import { useSnackbar } from "notistack";
import {
  downloadComponent,
  deleteComponentDownload,
  getComponentDownloadStatus,
} from "../../../api/component";
import { startJobPolling } from "../../../utils/jobPoller";

const formatSize = (bytes) => {
  if (bytes == null) return "";
  const mb = bytes / 1024 / 1024;
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
  return `${Math.round(mb)} MB`;
};

const ComponentDownloadControl = ({ component, onStatusChange }) => {
  const { t } = useTranslation(["common"]);
  const { enqueueSnackbar } = useSnackbar();
  const meta = component.metadata || {};
  const [downloaded, setDownloaded] = useState(Boolean(component.downloaded));
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    setDownloaded(Boolean(component.downloaded));
  }, [component.name, component.downloaded]);

  if (!meta.requires_download) return null;

  const finish = (isDownloaded) => {
    setDownloading(false);
    setDownloaded(isDownloaded);
    if (onStatusChange) onStatusChange(isDownloaded);
  };

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const { id } = await downloadComponent(component.name);
      startJobPolling(
        id,
        async () => {
          const status = await getComponentDownloadStatus(component.name);
          finish(status.downloaded);
          enqueueSnackbar(t("common:componentDownload.done"), {
            variant: "success",
          });
        },
        () => {
          finish(false);
          enqueueSnackbar(t("common:componentDownload.failed"), {
            variant: "error",
          });
        },
      );
    } catch (e) {
      finish(false);
      enqueueSnackbar(t("common:componentDownload.failed"), {
        variant: "error",
      });
    }
  };

  const handleDelete = async () => {
    await deleteComponentDownload(component.name);
    finish(false);
  };

  if (downloading) {
    return (
      <Box sx={{ my: 1 }}>
        <Typography variant="caption" color="text.secondary">
          {t("common:componentDownload.downloading")}
        </Typography>
        <LinearProgress sx={{ mt: 0.5 }} />
      </Box>
    );
  }

  if (downloaded) {
    return (
      <Button
        size="small"
        color="error"
        startIcon={<DeleteIcon />}
        onClick={handleDelete}
      >
        {t("common:componentDownload.delete")}
      </Button>
    );
  }

  return (
    <Button
      size="small"
      variant="outlined"
      startIcon={<DownloadIcon />}
      onClick={handleDownload}
    >
      {t("common:componentDownload.download", {
        size: formatSize(meta.download_size_bytes),
      })}
    </Button>
  );
};

export default ComponentDownloadControl;
