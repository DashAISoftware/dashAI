import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Box,
  Button,
  Chip,
  LinearProgress,
  Stack,
  Typography,
} from "@mui/material";
import {
  ATTACH_STATUS,
  FAILURE_CODE,
  FILE_STATUS,
  UPLOAD_PHASE,
} from "./uploadConstants";

const ITEM_LIST_MAX_HEIGHT = 320;

const STATUS_COLOR = Object.freeze({
  [FILE_STATUS.PENDING]: "default",
  [FILE_STATUS.UPLOADING]: "info",
  [FILE_STATUS.QUEUED]: "info",
  [FILE_STATUS.PROCESSING]: "info",
  [FILE_STATUS.READY]: "success",
  [FILE_STATUS.ERROR]: "error",
});

const STATUS_LABEL_KEY = Object.freeze({
  [FILE_STATUS.PENDING]: "generative:documentUpload.status.pending",
  [FILE_STATUS.UPLOADING]: "generative:documentUpload.status.uploading",
  [FILE_STATUS.QUEUED]: "generative:documentUpload.status.queued",
  [FILE_STATUS.PROCESSING]: "generative:documentUpload.status.processing",
  [FILE_STATUS.READY]: "generative:documentUpload.status.ready",
  [FILE_STATUS.ERROR]: "generative:documentUpload.status.error",
});

/**
 * @param {{code: string, detail: string}} failure - A failure descriptor.
 * @param {Function} t - Translation function.
 * @returns {string} The reason to show for it.
 */
function failureLabel(failure, t) {
  switch (failure.code) {
    case FAILURE_CODE.CANCELLED:
      return t("common:jobQueue.jobCancelled");
    case FAILURE_CODE.BATCH:
      return failure.detail || t("generative:documentUpload.batchFailed");
    case FAILURE_CODE.ENQUEUE:
      return t("generative:documentUpload.enqueueFailed", {
        reason:
          failure.detail || t("generative:documentUpload.parseFailedReason"),
      });
    case FAILURE_CODE.FOLDER_NAME:
      return t("generative:documentUpload.folderNameRequired");
    case FAILURE_CODE.PARSER:
      return t("generative:documentUpload.parserRequired");
    case FAILURE_CODE.TIMEOUT:
      return t("generative:documentUpload.timeoutReason");
    default:
      return t("generative:documentUpload.parseFailedReason");
  }
}

/**
 * Shows the per-file progress of an upload run and its final summary.
 *
 * @param {object}   props
 * @param {string}   props.phase - The upload phase.
 * @param {object}   props.progress - `{ completed, total, items }`.
 * @param {Array}    props.failures - Failures with `{ name, code, detail }`.
 * @param {Array}    props.skipped - Files left out by the picker.
 * @param {object}   props.attach - `{ status, ids, failure }`.
 * @param {string}   props.requestedFolderName - Folder name the user typed.
 * @param {string|null} props.resolvedFolderName - Folder name actually used.
 * @param {number}   props.renamedCount - Documents renamed to avoid a duplicate.
 * @param {Function} [props.onRetryAttach] - Retries the failed attach.
 * @param {object}   [props.titleRef] - Focus target for the dialog heading.
 * @returns {JSX.Element}
 */
export default function UploadProgressPanel({
  phase,
  progress,
  failures,
  skipped,
  attach,
  requestedFolderName,
  resolvedFolderName,
  renamedCount,
  onRetryAttach,
  titleRef,
}) {
  const { t } = useTranslation(["generative", "common"]);
  const total = progress.total;
  const completed = Math.min(progress.completed, total);
  const readyCount = progress.items.filter(
    (item) => item.status === FILE_STATUS.READY,
  ).length;
  const errorCount = progress.items.filter(
    (item) => item.status === FILE_STATUS.ERROR,
  ).length;
  const isProcessing = phase === UPLOAD_PHASE.PROCESSING;
  const isDone = phase === UPLOAD_PHASE.DONE;
  const percent = isDone
    ? total > 0
      ? Math.round((readyCount / total) * 100)
      : 0
    : total > 0
      ? Math.round((completed / total) * 100)
      : 0;
  const attachFailed = attach.status === ATTACH_STATUS.FAILED;
  const attachPending =
    attach.status === ATTACH_STATUS.PENDING && attach.ids.length > 0;
  const folderRenamed =
    resolvedFolderName != null &&
    resolvedFolderName !== requestedFolderName.trim();

  return (
    <Stack
      role="status"
      spacing={2}
      sx={{
        minWidth: 0,
        height: "100%",
        flex: 1,
        overflowY: "auto",
        overscrollBehavior: "contain",
        pr: 0.5,
      }}
    >
      <Box>
        <Typography
          ref={titleRef}
          tabIndex={-1}
          variant="subtitle1"
          sx={{ fontWeight: 600 }}
        >
          {t("generative:documentUpload.progressTitle")}
        </Typography>
        <Typography variant="body2" color="text.secondary" aria-live="polite">
          {t("generative:documentUpload.progressSummary", {
            completed,
            total,
          })}
        </Typography>
      </Box>

      <LinearProgress
        variant={isProcessing ? "indeterminate" : "determinate"}
        value={percent}
      />

      {folderRenamed && (
        <Alert severity="info">
          {t("generative:documentUpload.folderRenamed", {
            name: resolvedFolderName,
          })}
        </Alert>
      )}

      <Box
        sx={{
          flex: 1,
          minHeight: 0,
          maxHeight: ITEM_LIST_MAX_HEIGHT,
          overflowY: "auto",
          overscrollBehavior: "contain",
          border: 1,
          borderColor: "divider",
          borderRadius: 1,
          p: 1.5,
        }}
      >
        {progress.items.map((item) => {
          const basename = item.relativePath
            ? item.relativePath.split("/").pop()
            : item.name;
          return (
            <Box
              key={item.key}
              sx={{
                display: "flex",
                alignItems: "flex-start",
                justifyContent: "space-between",
                gap: 1.5,
                py: 0.75,
              }}
            >
              <Box sx={{ minWidth: 0, flex: 1 }}>
                <Typography
                  variant="body2"
                  noWrap
                  title={item.relativePath ?? item.name}
                >
                  {item.name}
                </Typography>
                {basename !== item.name && (
                  <Typography
                    variant="caption"
                    component="div"
                    color="text.secondary"
                    noWrap
                    title={item.relativePath}
                  >
                    {item.relativePath}
                  </Typography>
                )}
                {item.status === FILE_STATUS.ERROR && item.failure && (
                  <Typography variant="caption" color="error">
                    {failureLabel(item.failure, t)}
                  </Typography>
                )}
              </Box>
              <Chip
                size="small"
                variant="outlined"
                color={STATUS_COLOR[item.status] ?? "default"}
                label={t(
                  STATUS_LABEL_KEY[item.status] ??
                    STATUS_LABEL_KEY[FILE_STATUS.PENDING],
                )}
                sx={{
                  height: 20,
                  "& .MuiChip-label": { px: 0.75, fontSize: 11 },
                }}
              />
            </Box>
          );
        })}
      </Box>

      {!isDone && (
        <Typography variant="caption" color="text.secondary">
          {t("generative:documentUpload.processingNotice")}
        </Typography>
      )}

      {attachPending && (
        <Alert severity="info">
          {t("generative:documentUpload.attachRetrying")}
        </Alert>
      )}

      {attachFailed && (
        <Alert
          severity="error"
          action={
            onRetryAttach && (
              <Button color="inherit" size="small" onClick={onRetryAttach}>
                {t("generative:documentUpload.retryAttach")}
              </Button>
            )
          }
        >
          <Typography variant="body2">
            {t("generative:documentUpload.attachFailedSummary", {
              count: attach.ids.length,
            })}
          </Typography>
          {attach.failure?.detail && (
            <Typography variant="caption">{attach.failure.detail}</Typography>
          )}
        </Alert>
      )}

      {isDone && !attachFailed && !attachPending && (
        <Alert severity={errorCount > 0 ? "warning" : "success"}>
          <Typography variant="body2" aria-live="polite">
            {t("generative:documentUpload.doneSummary", { count: readyCount })}
          </Typography>
          {failures.length > 0 && (
            <Typography variant="body2">
              {t("generative:documentUpload.failedSummary", {
                count: failures.length,
              })}
            </Typography>
          )}
          {errorCount > 0 && (
            <Typography variant="body2">
              {t("generative:documentUpload.failedDocumentsInData")}
            </Typography>
          )}
          {renamedCount > 0 && (
            <Typography variant="body2">
              {t("generative:documentUpload.renamedSummary", {
                count: renamedCount,
              })}
            </Typography>
          )}
        </Alert>
      )}

      {skipped.length > 0 && (
        <Alert severity="info">
          <Typography variant="body2">
            {t("generative:documentUpload.skippedSummary", {
              count: skipped.length,
            })}
          </Typography>
        </Alert>
      )}
    </Stack>
  );
}

UploadProgressPanel.propTypes = {
  phase: PropTypes.string.isRequired,
  progress: PropTypes.shape({
    completed: PropTypes.number,
    total: PropTypes.number,
    items: PropTypes.arrayOf(PropTypes.object),
  }).isRequired,
  failures: PropTypes.arrayOf(PropTypes.object).isRequired,
  skipped: PropTypes.arrayOf(PropTypes.object).isRequired,
  attach: PropTypes.shape({
    status: PropTypes.string,
    ids: PropTypes.arrayOf(PropTypes.number),
    failure: PropTypes.object,
  }).isRequired,
  requestedFolderName: PropTypes.string.isRequired,
  resolvedFolderName: PropTypes.string,
  renamedCount: PropTypes.number,
  onRetryAttach: PropTypes.func,
  titleRef: PropTypes.shape({ current: PropTypes.any }),
};
