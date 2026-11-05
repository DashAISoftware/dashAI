import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import { Alert, Box, Button, Typography, useMediaQuery } from "@mui/material";
import RAGAdvancedDialog from "../../../pages/generative/RAGSession/advanced/RAGAdvancedDialog";
import { getComponents } from "../../../api/component";
import { loadsDataKind } from "../../../utils/dataKinds";
import DocumentSourcePicker from "./upload/DocumentSourcePicker";
import ExtensionParserConfig from "./upload/ExtensionParserConfig";
import UploadProgressPanel from "./upload/UploadProgressPanel";
import LargeSelectionDialog from "./upload/LargeSelectionDialog";
import CloseUploadConfirmDialog from "./upload/CloseUploadConfirmDialog";
import useDocumentUpload from "./upload/useDocumentUpload";
import {
  getFileExtension,
  getRootFolderName,
  groupByExtension,
} from "./upload/fileSelection";
import {
  ATTACH_CLOSE_TIMEOUT_MS,
  LOADERS_STATUS,
  SKIP_REASON,
  UPLOAD_MODE,
  UPLOAD_PHASE,
  UPLOAD_WARNING_THRESHOLD,
} from "./upload/uploadConstants";

/**
 * @param {object} loader - A DataLoader component.
 * @param {string} extension - A file extension, including the dot.
 * @returns {boolean} Whether that loader can parse the extension.
 */
function supportsExtension(loader, extension) {
  return (loader?.metadata?.supported_extensions ?? []).includes(extension);
}

/**
 * Upload dialog for RAG documents.
 *
 * Lets the user upload one folder or several loose files in a single pass. The
 * dialog only collects the selection, one parser per extension and its
 * parameters; the actual batch creation, per-file jobs and the single attach at
 * the end live in `useDocumentUpload`.
 *
 * @param {object}   props
 * @param {boolean}  props.open - Whether the dialog is open.
 * @param {Function} props.onClose - Called when the dialog asks to close.
 * @param {Function} props.onReady - Attaches finished ids; returns false when
 *   the attach failed.
 * @returns {JSX.Element}
 */
export default function RAGDocumentUpload({ open, onClose, onReady }) {
  const { t } = useTranslation(["generative", "common"]);
  const reduceMotion = useMediaQuery("(prefers-reduced-motion: reduce)");

  const [mode, setMode] = useState(UPLOAD_MODE.FILE);
  const [entries, setEntries] = useState([]);
  const [skipped, setSkipped] = useState([]);
  const [folderName, setFolderName] = useState("");
  const [folderNameTouched, setFolderNameTouched] = useState(false);
  const [loaders, setLoaders] = useState([]);
  const [loadersStatus, setLoadersStatus] = useState(LOADERS_STATUS.LOADING);
  const [selectedByExtension, setSelectedByExtension] = useState({});
  const [formErrors, setFormErrors] = useState({});
  const [missingDownloads, setMissingDownloads] = useState({});
  const [confirmLargeOpen, setConfirmLargeOpen] = useState(false);
  const [closeConfirmOpen, setCloseConfirmOpen] = useState(false);
  const formRefs = useRef({});
  const loadersRequestRef = useRef(0);
  const lastRootRef = useRef("");
  const mountedRef = useRef(true);
  const progressTitleRef = useRef(null);
  const upload = useDocumentUpload({ onReady });
  const { reset: resetUpload } = upload;

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const loadLoaders = useCallback(async () => {
    const requestId = loadersRequestRef.current + 1;
    loadersRequestRef.current = requestId;
    setLoadersStatus(LOADERS_STATUS.LOADING);
    setLoaders([]);
    try {
      const list = await getComponents({ selectTypes: ["DataLoader"] });
      if (!mountedRef.current || loadersRequestRef.current !== requestId)
        return;
      setLoaders(
        list.filter((component) => loadsDataKind(component, "document")),
      );
      setLoadersStatus(LOADERS_STATUS.READY);
    } catch {
      if (!mountedRef.current || loadersRequestRef.current !== requestId)
        return;
      setLoaders([]);
      setLoadersStatus(LOADERS_STATUS.ERROR);
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    setMode(UPLOAD_MODE.FILE);
    setEntries([]);
    setSkipped([]);
    setFolderName("");
    setFolderNameTouched(false);
    setSelectedByExtension({});
    setFormErrors({});
    setMissingDownloads({});
    setConfirmLargeOpen(false);
    setCloseConfirmOpen(false);
    setLoaders([]);
    lastRootRef.current = "";
    formRefs.current = {};
    resetUpload();
    loadLoaders();
  }, [open, resetUpload, loadLoaders]);

  useEffect(() => {
    if (upload.phase === UPLOAD_PHASE.UPLOADING) {
      progressTitleRef.current?.focus();
    }
  }, [upload.phase]);

  const loadersReady = loadersStatus === LOADERS_STATUS.READY;

  // A file whose extension no parser supports never reaches the batch: it is
  // reported as skipped instead of blocking the rest of the selection. While
  // the loaders are loading or failed nothing is classified as unsupported.
  const supportedEntries = useMemo(() => {
    if (!loadersReady) return entries;
    return entries.filter((entry) =>
      loaders.some((loader) =>
        supportsExtension(loader, getFileExtension(entry.file.name)),
      ),
    );
  }, [entries, loaders, loadersReady]);

  const unsupportedSkipped = useMemo(() => {
    if (!loadersReady) return [];
    return entries
      .filter(
        (entry) =>
          !loaders.some((loader) =>
            supportsExtension(loader, getFileExtension(entry.file.name)),
          ),
      )
      .map((entry) => ({
        relativePath: entry.relativePath,
        reason: SKIP_REASON.UNSUPPORTED,
      }));
  }, [entries, loaders, loadersReady]);

  const allSkipped = useMemo(
    () => [...skipped, ...unsupportedSkipped],
    [skipped, unsupportedSkipped],
  );

  const groupsByExtension = useMemo(
    () => groupByExtension(supportedEntries),
    [supportedEntries],
  );
  const extensions = useMemo(
    () => Object.keys(groupsByExtension).sort(),
    [groupsByExtension],
  );
  const selectionRoot = useMemo(
    () => getRootFolderName(supportedEntries),
    [supportedEntries],
  );

  // Every extension present in the selection gets a compatible parser, keeping
  // the user's choice when it is still valid.
  useEffect(() => {
    if (!loadersReady) return;
    setSelectedByExtension((previous) => {
      const next = {};
      let changed = false;
      for (const extension of extensions) {
        const compatible = loaders.filter((loader) =>
          supportsExtension(loader, extension),
        );
        const current = previous[extension];
        const resolved = compatible.some((loader) => loader.name === current)
          ? current
          : (compatible[0]?.name ?? null);
        next[extension] = resolved;
        if (resolved !== current) changed = true;
      }
      if (
        !changed &&
        Object.keys(previous).length === Object.keys(next).length
      ) {
        return previous;
      }
      return next;
    });
  }, [extensions, loaders, loadersReady]);

  // Folders picked through either input or a drop already carry a root name;
  // follow it while the value still is the previous root, and keep a name the
  // user typed themselves even when a new selection arrives.
  useEffect(() => {
    const previousRoot = lastRootRef.current;
    lastRootRef.current = selectionRoot;
    if (mode !== UPLOAD_MODE.FOLDER) return;
    if (folderNameTouched && folderName !== previousRoot) return;
    if (folderName === selectionRoot) return;
    setFolderName(selectionRoot);
    setFolderNameTouched(false);
  }, [selectionRoot, mode]);

  const registerFormRef = useCallback((loaderName, ref) => {
    formRefs.current[loaderName] = ref;
  }, []);

  const handleFormErrorChange = useCallback((loaderName, hasError) => {
    setFormErrors((previous) =>
      previous[loaderName] === hasError
        ? previous
        : { ...previous, [loaderName]: hasError },
    );
  }, []);

  const handleDownloadGateChange = useCallback((loaderName, missing) => {
    setMissingDownloads((previous) =>
      previous[loaderName] === missing
        ? previous
        : { ...previous, [loaderName]: missing },
    );
  }, []);

  const handleSelectLoader = useCallback((extension, loaderName) => {
    setSelectedByExtension((previous) => ({
      ...previous,
      [extension]: loaderName,
    }));
  }, []);

  const handleSelectionChange = useCallback((selection) => {
    setEntries(selection.accepted);
    setSkipped(selection.skipped);
    setMode((previous) =>
      selection.hasDirectory ? UPLOAD_MODE.FOLDER : previous,
    );
  }, []);

  const handleModeChange = useCallback((nextMode) => {
    setMode(nextMode);
  }, []);

  const handleFolderNameChange = useCallback((value) => {
    setFolderName(value);
    setFolderNameTouched(true);
  }, []);

  const selectedLoaders = useMemo(() => {
    const names = new Set(Object.values(selectedByExtension).filter(Boolean));
    return loaders.filter((loader) => names.has(loader.name));
  }, [loaders, selectedByExtension]);

  const missingParser = extensions.some(
    (extension) => !selectedByExtension[extension],
  );
  const formHasErrors = selectedLoaders.some((loader) =>
    Boolean(formErrors[loader.name]),
  );
  const downloadMissing = selectedLoaders.some((loader) =>
    Boolean(missingDownloads[loader.name]),
  );
  const folderNameInvalid = mode === UPLOAD_MODE.FOLDER && !folderName.trim();
  const uploadLocked =
    upload.phase === UPLOAD_PHASE.UPLOADING ||
    upload.phase === UPLOAD_PHASE.PROCESSING;
  const isDone = upload.phase === UPLOAD_PHASE.DONE;
  const canUpload =
    loadersReady &&
    supportedEntries.length > 0 &&
    extensions.length > 0 &&
    !missingParser &&
    !formHasErrors &&
    !downloadMissing &&
    !folderNameInvalid &&
    !upload.busy;

  /**
   * Collects the parser and parameters of every extension.
   *
   * @returns {Record<string, {loaderName: string, params: object}>} The map
   *   the upload hook needs to build the batch.
   */
  const buildParsers = () => {
    const parsers = {};
    for (const extension of extensions) {
      const loaderName = selectedByExtension[extension];
      const formRef = formRefs.current[loaderName];
      parsers[extension] = {
        loaderName,
        params: formRef?.current?.values ?? {},
      };
    }
    return parsers;
  };

  const handleClose = () => {
    if (uploadLocked) {
      setCloseConfirmOpen(true);
      return;
    }
    upload.reset();
    onClose();
  };

  const handleConfirmClose = async () => {
    setCloseConfirmOpen(false);
    await Promise.race([
      upload.attachReadyNow(),
      new Promise((resolve) => setTimeout(resolve, ATTACH_CLOSE_TIMEOUT_MS)),
    ]);
    upload.abort();
    upload.reset();
    onClose();
  };

  const startUpload = async () => {
    setConfirmLargeOpen(false);
    if (!canUpload) return;
    await upload.start({
      mode,
      folderName,
      entries: supportedEntries,
      skipped: allSkipped,
      parsers: buildParsers(),
    });
  };

  const handleUpload = () => {
    if (!canUpload) return;
    if (supportedEntries.length > UPLOAD_WARNING_THRESHOLD) {
      setConfirmLargeOpen(true);
      return;
    }
    startUpload();
  };

  return (
    <RAGAdvancedDialog
      open={open}
      onClose={handleClose}
      title={t("generative:documentsBar.uploadTitle")}
      maxWidth={false}
      minHeight={0}
      paperSx={{
        height: "90vh",
        maxWidth: "min(1680px, 95vw)",
        bgcolor: "background.paper",
        backgroundImage: "none",
      }}
      contentSx={{ p: 0, display: "flex", minHeight: 0, overflow: "hidden" }}
      actions={
        <>
          <Button onClick={handleClose}>
            {isDone ? t("common:close") : t("common:cancel")}
          </Button>
          {!isDone && (
            <Button
              variant="contained"
              loading={upload.busy && !reduceMotion}
              disabled={!canUpload}
              onClick={handleUpload}
            >
              {t("generative:documentsBar.upload")}
            </Button>
          )}
        </>
      }
    >
      {upload.phase === UPLOAD_PHASE.SELECTING ? (
        <Box
          sx={{
            display: "flex",
            flex: 1,
            minHeight: 0,
            minWidth: 0,
            flexDirection: { xs: "column", md: "row" },
          }}
        >
          <Box
            sx={{
              flex: 3,
              minWidth: 0,
              minHeight: 0,
              overflowY: "auto",
              overscrollBehavior: "contain",
              p: 2,
            }}
          >
            <DocumentSourcePicker
              mode={mode}
              onModeChange={handleModeChange}
              entries={supportedEntries}
              skipped={allSkipped}
              onSelectionChange={handleSelectionChange}
              folderName={folderName}
              onFolderNameChange={handleFolderNameChange}
              folderNameError={folderNameInvalid && supportedEntries.length > 0}
              disabled={upload.busy}
            />
          </Box>
          <Box
            sx={{
              flex: 2,
              minWidth: 0,
              minHeight: 0,
              display: "flex",
              flexDirection: "column",
              borderLeft: { xs: 0, md: 1 },
              borderTop: { xs: 1, md: 0 },
              borderColor: "divider",
              p: 2,
            }}
          >
            {loadersStatus === LOADERS_STATUS.ERROR ? (
              <Alert
                severity="error"
                action={
                  <Button color="inherit" size="small" onClick={loadLoaders}>
                    {t("generative:documentUpload.retryLoaders")}
                  </Button>
                }
              >
                {t("generative:documentUpload.loadersFailed")}
              </Alert>
            ) : loadersStatus === LOADERS_STATUS.LOADING ? (
              <Box
                sx={{
                  flex: 1,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "text.secondary",
                }}
              >
                <Typography variant="body2">
                  {t("generative:rag.common.loading")}
                </Typography>
              </Box>
            ) : supportedEntries.length === 0 ? (
              <Box
                sx={{
                  flex: 1,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  textAlign: "center",
                  color: "text.secondary",
                }}
              >
                <Typography variant="body2">
                  {t("generative:documentUpload.selectFilesToConfigure")}
                </Typography>
              </Box>
            ) : (
              <ExtensionParserConfig
                extensions={extensions}
                groupsByExtension={groupsByExtension}
                loaders={loaders}
                selectedByExtension={selectedByExtension}
                onSelectLoader={handleSelectLoader}
                registerFormRef={registerFormRef}
                onFormErrorChange={handleFormErrorChange}
                onDownloadGateChange={handleDownloadGateChange}
                disabled={upload.busy}
              />
            )}
          </Box>
        </Box>
      ) : (
        <Box
          sx={{
            flex: 1,
            minHeight: 0,
            display: "flex",
            p: 2,
            minWidth: 0,
          }}
        >
          <UploadProgressPanel
            phase={upload.phase}
            progress={upload.progress}
            failures={upload.failures}
            skipped={upload.skipped}
            attach={upload.attach}
            requestedFolderName={folderName}
            resolvedFolderName={upload.resolvedFolderName}
            renamedCount={upload.renamedCount}
            onRetryAttach={upload.retryAttach}
            titleRef={progressTitleRef}
          />
        </Box>
      )}

      <LargeSelectionDialog
        open={confirmLargeOpen}
        count={supportedEntries.length}
        onCancel={() => setConfirmLargeOpen(false)}
        onConfirm={startUpload}
      />

      <CloseUploadConfirmDialog
        open={closeConfirmOpen}
        onCancel={() => setCloseConfirmOpen(false)}
        onConfirm={handleConfirmClose}
      />
    </RAGAdvancedDialog>
  );
}

RAGDocumentUpload.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onReady: PropTypes.func.isRequired,
};
