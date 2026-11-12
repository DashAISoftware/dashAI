import React, { useRef, useState } from "react";
import PropTypes from "prop-types";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  IconButton,
  Modal,
  Tooltip,
  Typography,
} from "@mui/material";
import { Close as CloseIcon, FileDownload } from "@mui/icons-material";
import { useTranslation } from "react-i18next";
import { useSnackbar } from "notistack";
import { useNavigate } from "react-router-dom";
import { importGenerativeSession } from "../../api/session";
import { describeSessionImportError } from "../../utils/sessionImportError";
import { startComponentDownload } from "../models/model/ComponentDownloadControl";
import { standaloneRouteFor } from "./standaloneEntryPoints";

/**
 * Header button that imports a .dashai file as a new generative session.
 *
 * The file only holds a configuration, so it opens the file picker right
 * away. While the request runs a modal shows progress; when the import has
 * something to report (version warnings, models to download) the modal shows
 * it until the user closes it, otherwise a success snackbar is enough.
 *
 * Opening a session changes the route, which remounts the session list and
 * this button with it, so the app navigates to the new session only once the
 * modal is closed: navigating first would drop the report unread.
 */
export default function ImportGenerativeSessionButton({ onImported }) {
  const { t } = useTranslation(["generative", "models", "common"]);
  const { enqueueSnackbar } = useSnackbar();
  const navigate = useNavigate();
  const inputRef = useRef(null);
  // "closed" | "importing" | "result" | "error"
  const [phase, setPhase] = useState("closed");
  const [result, setResult] = useState(null);
  const [importError, setImportError] = useState(null);
  const [downloadStarted, setDownloadStarted] = useState(false);

  const importing = phase === "importing";

  const close = () => {
    if (importing) return;
    setPhase("closed");
    if (phase === "result" && result) navigate(sessionRoute(result));
  };

  const sessionRoute = (imported) => {
    const standaloneRoute = standaloneRouteFor(imported.task_name);
    return standaloneRoute
      ? `${standaloneRoute}/sessions/${imported.session_id}`
      : `/app/generative/sessions/${imported.session_id}`;
  };

  const handleFile = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setPhase("importing");
    try {
      const imported = await importGenerativeSession(file);
      await onImported?.();
      if (imported.warnings.length > 0 || imported.needs_download.length > 0) {
        setResult(imported);
        setDownloadStarted(false);
        setPhase("result");
      } else {
        setPhase("closed");
        navigate(sessionRoute(imported));
        enqueueSnackbar(
          t("generative:label.sessionImported", {
            session: imported.session_name,
          }),
          { variant: "success" },
        );
      }
    } catch (error) {
      setImportError(
        describeSessionImportError(error, t, {
          messageKeys: { wrong_kind: "generative:importError.wrongKind" },
        }),
      );
      setPhase("error");
    }
  };

  const goToPlugins = () => {
    const link = importError?.pluginsLink;
    close();
    navigate(link);
  };

  const downloadMissing = () => {
    setDownloadStarted(true);
    result.needs_download.forEach((component) =>
      startComponentDownload({ component, enqueueSnackbar, t }),
    );
  };

  const renderBody = () => {
    if (importing) {
      return (
        <Box sx={{ display: "flex", alignItems: "center", gap: 2, py: 2 }}>
          <CircularProgress size={28} />
          <Typography>{t("models:label.importingSession")}</Typography>
        </Box>
      );
    }

    if (phase === "error") {
      return (
        <>
          <Alert severity="error">{importError?.message}</Alert>
          <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 2 }}>
            {importError?.pluginsLink ? (
              <>
                <Button onClick={close} sx={{ color: "text.secondary" }}>
                  {t("common:close")}
                </Button>
                <Button variant="contained" onClick={goToPlugins}>
                  {t("models:button.goToPlugins")}
                </Button>
              </>
            ) : (
              <Button variant="contained" onClick={close}>
                {t("common:close")}
              </Button>
            )}
          </Box>
        </>
      );
    }

    if (phase === "result" && result) {
      return (
        <>
          <Alert severity="success">
            {t("generative:label.sessionImported", {
              session: result.session_name,
            })}
          </Alert>
          {result.warnings.map((warning) => (
            <Alert key={warning} severity="warning">
              {warning}
            </Alert>
          ))}
          {result.needs_download.length > 0 && (
            <Alert
              severity="warning"
              sx={{ "& .MuiAlert-action": { alignItems: "center", pt: 0 } }}
              action={
                <Button
                  color="inherit"
                  size="small"
                  disabled={downloadStarted}
                  onClick={downloadMissing}
                >
                  {downloadStarted
                    ? t("common:componentDownload.downloading")
                    : t("common:componentDownload.download")}
                </Button>
              }
            >
              {t("generative:label.importedNeedsDownload", {
                names: result.needs_download
                  .map((component) => component.display_name)
                  .join(", "),
              })}
            </Alert>
          )}
          <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
            <Button variant="contained" onClick={close}>
              {t("models:button.gotIt")}
            </Button>
          </Box>
        </>
      );
    }
    return null;
  };

  const title =
    phase === "result"
      ? t("models:label.sessionImportedTitle")
      : t("models:button.importSession");

  return (
    <>
      <Tooltip title={t("models:button.importSession")}>
        <span>
          <IconButton
            size="small"
            disabled={importing}
            onClick={() => inputRef.current?.click()}
            aria-label={t("models:button.importSession")}
          >
            {importing ? (
              <CircularProgress size={16} />
            ) : (
              <FileDownload sx={{ fontSize: 18 }} />
            )}
          </IconButton>
        </span>
      </Tooltip>
      <input
        ref={inputRef}
        type="file"
        accept=".dashai"
        hidden
        onChange={handleFile}
        data-testid="generative-import-input"
      />
      <Modal
        open={phase !== "closed"}
        onClose={close}
        disableEscapeKeyDown={importing}
      >
        <Box
          onClick={(e) => e.stopPropagation()}
          sx={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            width: { xs: "90%", sm: 480 },
            bgcolor: "background.paper",
            borderRadius: 2,
            boxShadow: 12,
            outline: "none",
          }}
        >
          <Box
            sx={{
              p: 2,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <Typography variant="h6" component="h2">
              {title}
            </Typography>
            {!importing && (
              <IconButton
                onClick={close}
                size="small"
                aria-label={t("common:close")}
                sx={{ color: "text.secondary" }}
              >
                <CloseIcon />
              </IconButton>
            )}
          </Box>
          <Box
            sx={{
              p: 3,
              pt: 0,
              display: "flex",
              flexDirection: "column",
              gap: 2,
            }}
          >
            {renderBody()}
          </Box>
        </Box>
      </Modal>
    </>
  );
}

ImportGenerativeSessionButton.propTypes = {
  onImported: PropTypes.func,
};
