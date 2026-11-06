import { useEffect, useId, useRef, useState } from "react";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Box,
  Button,
  ButtonBase,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  TextField,
  ToggleButton,
  Typography,
} from "@mui/material";
import InsertDriveFileIcon from "@mui/icons-material/InsertDriveFile";
import FolderIcon from "@mui/icons-material/Folder";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import VisibilityIcon from "@mui/icons-material/Visibility";
import { useTheme } from "@mui/material/styles";
import PillToggleButtonGroup from "../../../shared/PillToggleButtonGroup";
import {
  getRootFolderNames,
  readDroppedEntries,
  readSelectedFiles,
} from "./fileSelection";
import {
  formatFileSize,
  MAX_FILE_SIZE_BYTES,
  SKIP_REASON,
  UPLOAD_MODE,
} from "./uploadConstants";

const SKIPPED_LIST_MAX_HEIGHT = 120;

/**
 * @param {string} reason - A skip reason constant.
 * @param {Function} t - Translation function.
 * @returns {string} The readable reason for the skipped files list.
 */
function skipReasonLabel(reason, t) {
  switch (reason) {
    case SKIP_REASON.HIDDEN:
      return t("generative:documentUpload.skipReasons.hidden");
    case SKIP_REASON.SYSTEM:
      return t("generative:documentUpload.skipReasons.system");
    case SKIP_REASON.EMPTY:
      return t("generative:documentUpload.skipReasons.empty");
    case SKIP_REASON.TOO_LARGE:
      return t("generative:documentUpload.skipReasons.tooLarge", {
        limit: formatFileSize(MAX_FILE_SIZE_BYTES),
      });
    case SKIP_REASON.UNSUPPORTED:
      return t("generative:documentUpload.skipReasons.unsupported");
    case SKIP_REASON.READ_ERROR:
      return t("generative:documentUpload.skipReasons.readError");
    default:
      return t("generative:documentUpload.skipReasons.readError");
  }
}

/**
 * One row of the selected-files list. PDFs are clickable and open a local
 * preview; other formats stay as plain rows.
 *
 * @param {object}   props
 * @param {object}   props.entry - A `{file, relativePath}` selection entry.
 * @param {Function} props.onPreview - Called with the file to preview.
 * @returns {JSX.Element}
 */
function SelectedFileRow({ entry, onPreview }) {
  const isPdf =
    entry.file.type === "application/pdf" ||
    entry.file.name.toLowerCase().endsWith(".pdf");
  const Row = isPdf ? ButtonBase : Box;

  return (
    <Row
      onClick={isPdf ? () => onPreview(entry.file) : undefined}
      aria-label={isPdf ? entry.file.name : undefined}
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1,
        width: "100%",
        minWidth: 0,
        minHeight: 36,
        px: 0.75,
        borderRadius: 1,
        textAlign: "left",
        justifyContent: "flex-start",
        ...(isPdf && {
          cursor: "pointer",
          "@media (hover: hover)": {
            "&:hover": { bgcolor: "action.hover" },
          },
          "&.Mui-focusVisible": {
            outline: "2px solid",
            outlineColor: "primary.main",
            outlineOffset: -2,
          },
        }),
      }}
    >
      <InsertDriveFileIcon
        fontSize="small"
        color={isPdf ? "primary" : "disabled"}
      />
      <Box
        component="span"
        sx={{
          display: "flex",
          flexDirection: "column",
          minWidth: 0,
          flex: 1,
        }}
      >
        <Typography
          variant="body2"
          component="span"
          noWrap
          title={entry.relativePath}
          sx={{ display: "block" }}
        >
          {entry.file.name}
        </Typography>
        {entry.relativePath !== entry.file.name && (
          <Typography
            variant="caption"
            component="span"
            color="text.secondary"
            noWrap
            title={entry.relativePath}
            sx={{ display: "block" }}
          >
            {entry.relativePath}
          </Typography>
        )}
      </Box>
      {isPdf && (
        <VisibilityIcon fontSize="small" color="action" aria-hidden="true" />
      )}
    </Row>
  );
}

/**
 * Source picker for the upload dialog: drop zone, file/folder buttons, the
 * optional folder name, and the summary of what was accepted and skipped.
 *
 * @param {object}   props
 * @param {string}   props.mode - "file" or "folder".
 * @param {Function} props.onModeChange - Switches between the two modes.
 * @param {Array}    props.entries - Accepted entries of the current selection.
 * @param {Array}    props.skipped - Skipped entries with their reason.
 * @param {Function} props.onSelectionChange - Receives a new selection.
 * @param {string}   props.folderName - Folder name typed by the user.
 * @param {Function} props.onFolderNameChange - Updates the folder name.
 * @param {boolean}  props.folderNameError - Marks the folder name as required.
 * @param {boolean}  props.disabled - Whether the upload already started.
 * @returns {JSX.Element}
 */
export default function DocumentSourcePicker({
  mode,
  onModeChange,
  entries,
  skipped,
  onSelectionChange,
  folderName,
  onFolderNameChange,
  folderNameError,
  disabled,
}) {
  const { t } = useTranslation(["generative", "common"]);
  const theme = useTheme();
  const filesInputRef = useRef(null);
  const folderInputRef = useRef(null);
  const hintId = useId();
  const [dragActive, setDragActive] = useState(false);
  const [dropError, setDropError] = useState(false);
  const [previewFile, setPreviewFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");

  useEffect(() => {
    if (!previewFile) {
      setPreviewUrl("");
      return undefined;
    }
    const url = URL.createObjectURL(previewFile);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [previewFile]);

  const rootFolderNames = getRootFolderNames(entries);
  const rootFolderName = rootFolderNames[0] ?? "";
  const multipleRoots =
    mode === UPLOAD_MODE.FOLDER && rootFolderNames.length > 1;

  // React does not forward `webkitdirectory` reliably on every version; setting
  // it on the node keeps folder picking working regardless.
  useEffect(() => {
    const input = folderInputRef.current;
    if (!input) return;
    input.setAttribute("webkitdirectory", "");
    input.setAttribute("directory", "");
  }, []);

  const handleInputChange = (event, hasDirectory) => {
    const fileList = event.target.files;
    if (!fileList || fileList.length === 0) {
      // A cancelled pick must not discard the previous selection.
      event.target.value = "";
      return;
    }
    const selection = readSelectedFiles(fileList);
    // Clearing the value lets the user pick the very same files again.
    event.target.value = "";
    onSelectionChange({ ...selection, hasDirectory });
  };

  const handleDrop = async (event) => {
    event.preventDefault();
    event.stopPropagation();
    setDragActive(false);
    if (disabled) return;
    try {
      setDropError(false);
      const selection = await readDroppedEntries(event.dataTransfer);
      onSelectionChange(selection);
    } catch {
      setDropError(true);
    }
  };

  const handleDragOver = (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (!disabled) setDragActive(true);
  };

  const handleDragLeave = (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (event.currentTarget.contains(event.relatedTarget)) return;
    setDragActive(false);
  };

  return (
    <>
      <Stack spacing={2} sx={{ minWidth: 0, height: "100%", minHeight: 0 }}>
        <PillToggleButtonGroup
          fullWidth
          value={mode}
          onChange={(_event, value) => value && onModeChange(value)}
          disabled={disabled}
          aria-label={t("generative:documentUpload.sourceModeLabel")}
          sx={{
            "& .MuiToggleButtonGroup-grouped": {
              minHeight: 40,
              flex: 1,
              gap: 1,
              px: 2,
              fontSize: "0.85rem",
              fontWeight: 400,
              textTransform: "none",
              border: "1px solid transparent",
              borderRadius: "4px !important",
              color: "text.secondary",
              "&:hover": { bgcolor: "action.hover" },
              "&.Mui-selected": {
                bgcolor: theme.palette.accent.purpleDim,
                color: theme.palette.accent.purple,
                fontWeight: 600,
                borderBottom: "2px solid",
                borderBottomColor: theme.palette.accent.purple,
                "&:hover": { bgcolor: theme.palette.accent.purpleDim },
              },
            },
          }}
        >
          <ToggleButton value={UPLOAD_MODE.FILE}>
            <InsertDriveFileIcon fontSize="small" />
            {t("generative:documentUpload.modeFile")}
          </ToggleButton>
          <ToggleButton value={UPLOAD_MODE.FOLDER}>
            <FolderIcon fontSize="small" />
            {t("generative:documentUpload.modeFolder")}
          </ToggleButton>
        </PillToggleButtonGroup>

        <Box
          role="group"
          aria-label={t("generative:documentUpload.dropzoneLabel")}
          aria-describedby={hintId}
          onDragEnter={handleDragOver}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 1,
            p: 3,
            minHeight: 180,
            border: 2,
            borderStyle: "dashed",
            borderRadius: 2,
            borderColor: dragActive ? "primary.main" : "divider",
            bgcolor: dragActive ? "action.hover" : "background.default",
            textAlign: "center",
            transition:
              "border-color 150ms ease-out, background-color 150ms ease-out",
          }}
        >
          <CloudUploadIcon color="primary" sx={{ fontSize: 36 }} />
          <Typography id={hintId} variant="body2" color="text.secondary">
            {t("generative:documentUpload.dropzoneHint")}
          </Typography>
          <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
            <Button
              variant="outlined"
              size="small"
              disabled={disabled}
              sx={{ minHeight: 44 }}
              onClick={() => filesInputRef.current?.click()}
            >
              {t("generative:documentUpload.selectFiles")}
            </Button>
            <Button
              variant="outlined"
              size="small"
              disabled={disabled}
              sx={{ minHeight: 44 }}
              onClick={() => folderInputRef.current?.click()}
            >
              {t("generative:documentUpload.selectFolder")}
            </Button>
          </Stack>
          <input
            ref={filesInputRef}
            type="file"
            multiple
            style={{ display: "none" }}
            onChange={(event) => handleInputChange(event, false)}
          />
          <input
            ref={folderInputRef}
            type="file"
            multiple
            style={{ display: "none" }}
            onChange={(event) => handleInputChange(event, true)}
          />
        </Box>

        {dropError && (
          <Alert severity="error" onClose={() => setDropError(false)}>
            {t("generative:documentUpload.dropFailed")}
          </Alert>
        )}

        {mode === UPLOAD_MODE.FOLDER && (
          <TextField
            size="small"
            fullWidth
            required
            label={t("generative:documentUpload.folderNameLabel")}
            value={folderName}
            onChange={(event) => onFolderNameChange(event.target.value)}
            error={folderNameError}
            helperText={
              folderNameError
                ? t("generative:documentUpload.folderNameRequired")
                : t("generative:documentUpload.folderNameHint")
            }
            disabled={disabled}
          />
        )}

        {multipleRoots && (
          <Alert severity="info">
            {t("generative:documentUpload.multipleRootFolders", {
              count: rootFolderNames.length,
              name: folderName.trim() || rootFolderName,
            })}
          </Alert>
        )}

        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            gap: 1,
            flex: 1,
            minHeight: 0,
          }}
        >
          <Typography
            variant="body2"
            sx={{ fontWeight: 600 }}
            aria-live="polite"
          >
            {t("generative:documentUpload.selectionSummary", {
              count: entries.length,
            })}
          </Typography>
          {mode === UPLOAD_MODE.FOLDER && rootFolderName && (
            <Typography variant="caption" color="text.secondary">
              {t("generative:documentUpload.rootFolder", {
                name: rootFolderName,
              })}
            </Typography>
          )}
          {mode === UPLOAD_MODE.FOLDER &&
            rootFolderName &&
            folderName.trim() &&
            folderName.trim() !== rootFolderName && (
              <Typography variant="caption" color="text.secondary">
                {t("generative:documentUpload.folderNameOverride", {
                  name: folderName.trim(),
                })}
              </Typography>
            )}
          {entries.length > 0 && (
            <Box
              sx={{
                flex: 1,
                minHeight: 0,
                display: "flex",
                flexDirection: "column",
                gap: 0.25,
                overflowY: "auto",
                overscrollBehavior: "contain",
                border: 1,
                borderColor: "divider",
                borderRadius: 1,
                p: 1,
              }}
            >
              {entries.map((entry, index) => (
                <SelectedFileRow
                  key={`${entry.relativePath}#${index}`}
                  entry={entry}
                  onPreview={setPreviewFile}
                />
              ))}
            </Box>
          )}
          {skipped.length > 0 && (
            <Alert
              severity="warning"
              sx={{ whiteSpace: "normal", flexShrink: 0 }}
            >
              <Typography
                variant="body2"
                sx={{ fontWeight: 600 }}
                aria-live="polite"
              >
                {t("generative:documentUpload.skippedSummary", {
                  count: skipped.length,
                })}
              </Typography>
              <Box
                sx={{
                  maxHeight: SKIPPED_LIST_MAX_HEIGHT,
                  overflowY: "auto",
                  overscrollBehavior: "contain",
                  mt: 0.5,
                }}
              >
                {skipped.map((entry, index) => (
                  <Typography
                    key={`${entry.relativePath}#${index}`}
                    variant="caption"
                    component="div"
                    noWrap
                    title={entry.relativePath}
                  >
                    {entry.relativePath} — {skipReasonLabel(entry.reason, t)}
                  </Typography>
                ))}
              </Box>
            </Alert>
          )}
        </Box>
      </Stack>
      <Dialog
        open={Boolean(previewFile)}
        onClose={() => setPreviewFile(null)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          {previewFile?.name ?? t("documentsBar.preview")}
        </DialogTitle>
        <DialogContent sx={{ p: 0, height: "75vh", overflow: "hidden" }}>
          {previewUrl && (
            <Box
              component="iframe"
              title={previewFile.name}
              src={previewUrl}
              sx={{
                display: "block",
                width: "100%",
                height: "100%",
                border: 0,
              }}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewFile(null)}>
            {t("common:close")}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

SelectedFileRow.propTypes = {
  entry: PropTypes.object.isRequired,
  onPreview: PropTypes.func.isRequired,
};

DocumentSourcePicker.propTypes = {
  mode: PropTypes.oneOf([UPLOAD_MODE.FILE, UPLOAD_MODE.FOLDER]).isRequired,
  onModeChange: PropTypes.func.isRequired,
  entries: PropTypes.arrayOf(PropTypes.object).isRequired,
  skipped: PropTypes.arrayOf(PropTypes.object).isRequired,
  onSelectionChange: PropTypes.func.isRequired,
  folderName: PropTypes.string.isRequired,
  onFolderNameChange: PropTypes.func.isRequired,
  folderNameError: PropTypes.bool,
  disabled: PropTypes.bool,
};
