import React from "react";
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Stack,
  Typography,
} from "@mui/material";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import SaveIcon from "@mui/icons-material/Save";
import CodeIcon from "@mui/icons-material/Code";
import { useTranslation } from "react-i18next";
import CodeEditor from "./CodeEditor";
import ValidationStatus from "./ValidationStatus";
import { useCustomComponents } from "./CustomComponentsContext";

const VALIDATION_SLOT_HEIGHT = 160;

export default function CustomComponentsCenter() {
  const { t } = useTranslation(["customComponents", "common"]);
  const {
    draft,
    setDraftField,
    validation,
    validating,
    saving,
    canSubmit,
    runValidate,
    save,
  } = useCustomComponents();

  const title = draft.isNew
    ? t("dialog.createTitle")
    : draft.class_name || t("dialog.editTitle");

  const showValidation = Boolean(validation);

  return (
    <Box
      height="100%"
      display="flex"
      flexDirection="column"
      sx={{ bgcolor: "background.default" }}
    >
      <Stack
        direction="row"
        alignItems="center"
        spacing={1}
        px={2}
        py={1}
        borderBottom="1px solid"
        borderColor="divider"
        flexShrink={0}
      >
        <CodeIcon fontSize="small" color="action" />
        <Typography
          variant="subtitle1"
          sx={{ fontFamily: "monospace", flexGrow: 1 }}
          noWrap
        >
          {title}
        </Typography>
        {draft.dirty && (
          <Chip
            size="small"
            label={t("center.unsaved")}
            color="warning"
            variant="outlined"
          />
        )}
        <Button
          size="small"
          onClick={runValidate}
          disabled={!canSubmit || validating || saving}
          startIcon={
            validating ? <CircularProgress size={14} /> : <PlayArrowIcon />
          }
        >
          {t("actions.validate")}
        </Button>
        <Button
          size="small"
          variant="contained"
          onClick={save}
          disabled={!canSubmit || saving}
          startIcon={saving ? <CircularProgress size={14} /> : <SaveIcon />}
        >
          {draft.isNew ? t("actions.create") : t("actions.update")}
        </Button>
      </Stack>

      <Box flexGrow={1} minHeight={0} p={1}>
        <CodeEditor
          value={draft.source_code}
          onChange={(v) => setDraftField({ source_code: v })}
        />
      </Box>

      <Divider
        sx={{
          opacity: showValidation ? 1 : 0,
          transition: "opacity 0.15s",
          flexShrink: 0,
        }}
      />
      <Box
        sx={{
          height: showValidation ? VALIDATION_SLOT_HEIGHT : 0,
          overflow: "auto",
          transition: "height 0.2s ease",
          flexShrink: 0,
          px: showValidation ? 2 : 0,
          py: showValidation ? 1 : 0,
        }}
      >
        {showValidation && <ValidationStatus result={validation} />}
      </Box>
    </Box>
  );
}
