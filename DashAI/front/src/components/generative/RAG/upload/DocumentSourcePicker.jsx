import { useEffect, useId, useRef, useState } from "react";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Box,
  Button,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import InsertDriveFileIcon from "@mui/icons-material/InsertDriveFile";
import FolderIcon from "@mui/icons-material/Folder";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
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
const SELECTION_LIST_MAX_HEIGHT = 140;

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
  const { t } = useTranslation("generative");
  const filesInputRef = useRef(null);
  const folderInputRef = useRef(null);
  const hintId = useId();
  const [dragActive, setDragActive] = useState(false);
  const [dropError, setDropError] = useState(false);
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
    <Stack spacing={2} sx={{ minWidth: 0 }}>
      <ToggleButtonGroup
        exclusive
        size="small"
        value={mode}
        onChange={(_event, value) => value && onModeChange(value)}
        disabled={disabled}
        aria-label={t("generative:documentUpload.sourceModeLabel")}
      >
        <ToggleButton value={UPLOAD_MODE.FILE}>
          <InsertDriveFileIcon fontSize="small" sx={{ mr: 1 }} />
          {t("generative:documentUpload.modeFile")}
        </ToggleButton>
        <ToggleButton value={UPLOAD_MODE.FOLDER}>
          <FolderIcon fontSize="small" sx={{ mr: 1 }} />
          {t("generative:documentUpload.modeFolder")}
        </ToggleButton>
      </ToggleButtonGroup>

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

      <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
        <Typography variant="body2" sx={{ fontWeight: 600 }} aria-live="polite">
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
              maxHeight: SELECTION_LIST_MAX_HEIGHT,
              overflowY: "auto",
              overscrollBehavior: "contain",
              border: 1,
              borderColor: "divider",
              borderRadius: 1,
              p: 1,
            }}
          >
            {entries.map((entry, index) => (
              <Typography
                key={`${entry.relativePath}#${index}`}
                variant="caption"
                component="div"
                noWrap
                color="text.secondary"
                title={entry.relativePath}
              >
                {entry.relativePath}
              </Typography>
            ))}
          </Box>
        )}
        {skipped.length > 0 && (
          <Alert severity="warning" sx={{ whiteSpace: "normal" }}>
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
  );
}

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
