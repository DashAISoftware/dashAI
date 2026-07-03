import React, { useState, useEffect, useRef } from "react";
import {
  Box,
  Button,
  CircularProgress,
  IconButton,
  LinearProgress,
  Tooltip,
  Typography,
} from "@mui/material";
import DownloadIcon from "@mui/icons-material/Download";
import DeleteIcon from "@mui/icons-material/Delete";
import { useTranslation } from "react-i18next";
import { useSnackbar } from "notistack";
import {
  downloadComponent,
  deleteComponentDownload,
  getComponentDownloadStatus,
} from "../../../api/component";
import { startJobPolling, stopJobPolling } from "../../../utils/jobPoller";

const formatSize = (bytes) => {
  if (bytes == null) return "";
  const mb = bytes / 1024 / 1024;
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
  return `${Math.round(mb)} MB`;
};

// Download state is a global, per-component fact (a component's artifacts are
// either on disk or not). The same component can be rendered by several
// controls at once (e.g. the same model selected at multiple nesting levels).
// This module-level pub/sub keeps every mounted control for a given component
// name in sync, and the cache lets a freshly mounted control pick up the
// latest known state instead of the (possibly stale) prop.
const downloadListeners = new Map(); // name -> Set<(state) => void>
const downloadStateCache = new Map(); // name -> { downloading, downloaded }
const anyChangeListeners = new Set(); // (name, state) => void

const subscribeDownloadState = (name, listener) => {
  let listeners = downloadListeners.get(name);
  if (!listeners) {
    listeners = new Set();
    downloadListeners.set(name, listeners);
  }
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
};

// Subscribe to every download/delete regardless of component name. Lets a
// container (e.g. a config dialog) re-check which nested components still need
// downloading after an inline control finishes.
export const subscribeAnyDownloadState = (listener) => {
  anyChangeListeners.add(listener);
  return () => {
    anyChangeListeners.delete(listener);
  };
};

const broadcastDownloadState = (name, state) => {
  downloadStateCache.set(name, { ...downloadStateCache.get(name), ...state });
  const listeners = downloadListeners.get(name);
  if (listeners) listeners.forEach((listener) => listener(state));
  anyChangeListeners.forEach((listener) => listener(name, state));
};

const ComponentDownloadControl = ({
  component,
  onStatusChange,
  compact = false,
}) => {
  const { t } = useTranslation(["common"]);
  const { enqueueSnackbar } = useSnackbar();
  const meta = component.metadata || {};
  const cached = downloadStateCache.get(component.name);
  const [downloaded, setDownloaded] = useState(
    cached?.downloaded ?? Boolean(component.downloaded),
  );
  const [downloading, setDownloading] = useState(cached?.downloading ?? false);
  const pollerIdRef = useRef(null);

  useEffect(() => {
    const known = downloadStateCache.get(component.name);
    setDownloaded(known?.downloaded ?? Boolean(component.downloaded));
    setDownloading(known?.downloading ?? false);
  }, [component.name, component.downloaded]);

  // Mirror download/delete triggered by any other control for this component.
  useEffect(() => {
    return subscribeDownloadState(component.name, (state) => {
      if (state.downloading !== undefined) setDownloading(state.downloading);
      if (state.downloaded !== undefined) setDownloaded(state.downloaded);
    });
  }, [component.name]);

  useEffect(() => {
    return () => {
      if (pollerIdRef.current != null) stopJobPolling(pollerIdRef.current);
    };
  }, []);

  if (!meta.requires_download) return null;

  const finish = (isDownloaded) => {
    broadcastDownloadState(component.name, {
      downloading: false,
      downloaded: isDownloaded,
    });
    if (onStatusChange) onStatusChange(isDownloaded);
  };

  const handleDownload = async () => {
    broadcastDownloadState(component.name, { downloading: true });
    try {
      const { id } = await downloadComponent(component.name);
      pollerIdRef.current = id;
      startJobPolling(
        id,
        async () => {
          pollerIdRef.current = null;
          const status = await getComponentDownloadStatus(component.name);
          finish(status.downloaded);
          enqueueSnackbar(t("common:componentDownload.done"), {
            variant: "success",
          });
        },
        () => {
          pollerIdRef.current = null;
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
    try {
      await deleteComponentDownload(component.name);
      finish(false);
      enqueueSnackbar(t("common:componentDownload.deleted"), {
        variant: "success",
      });
    } catch {
      enqueueSnackbar(t("common:componentDownload.failed"), {
        variant: "error",
      });
    }
  };

  if (compact) {
    if (downloading) {
      return (
        <Tooltip title={t("common:componentDownload.downloading")}>
          <CircularProgress size={20} />
        </Tooltip>
      );
    }
    if (downloaded) {
      return (
        <Tooltip title={t("common:componentDownload.delete")}>
          <IconButton size="small" color="error" onClick={handleDelete}>
            <DeleteIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      );
    }
    return (
      <Tooltip
        title={t("common:componentDownload.download", {
          size: formatSize(meta.download_size_bytes),
        })}
      >
        <IconButton size="small" color="primary" onClick={handleDownload}>
          <DownloadIcon fontSize="small" />
        </IconButton>
      </Tooltip>
    );
  }

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
