import React, { useState } from "react";
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
import UndoIcon from "@mui/icons-material/Undo";
import CodeIcon from "@mui/icons-material/Code";
import { useTranslation } from "react-i18next";
import CodeEditor from "./CodeEditor";
import ValidationStatus from "./ValidationStatus";
import DeleteCustomComponentDialog from "./DeleteCustomComponentDialog";
import { useCustomComponents } from "./CustomComponentsContext";

const VALIDATION_SLOT_HEIGHT = 160;

function originChip(origin, t) {
  switch (origin) {
    case "custom":
      return { label: t("origin.custom"), color: "primary" };
    case "custom-override":
      return { label: t("origin.modified"), color: "warning" };
    case "core":
      return { label: t("origin.core"), color: "default" };
    case "plugin":
      return { label: t("origin.plugin"), color: "secondary" };
    default:
      return null;
  }
}

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
    revert,
    customRows,
  } = useCustomComponents();

  const [revertOpen, setRevertOpen] = useState(false);
  const showValidation = Boolean(validation);

  const title = draft.class_name
    ? draft.class_name
    : draft.isNew
      ? t("dialog.createTitle")
      : t("dialog.editTitle");

  const chip = originChip(draft.origin, t);
  const canRevert = draft.id != null && draft.isOverride;
  const revertRow = canRevert
    ? customRows.find((r) => r.id === draft.id)
    : null;

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
        {chip && (
          <Chip
            size="small"
            label={chip.label}
            color={chip.color}
            variant={chip.color === "default" ? "outlined" : "filled"}
          />
        )}
        {draft.dirty && (
          <Chip
            size="small"
            label={t("center.unsaved")}
            color="warning"
            variant="outlined"
          />
        )}
        {canRevert && (
          <Button
            size="small"
            color="warning"
            onClick={() => setRevertOpen(true)}
            disabled={saving}
            startIcon={<UndoIcon />}
          >
            {t("actions.revert")}
          </Button>
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
          {draft.id == null
            ? draft.isOverride
              ? t("actions.createOverride")
              : t("actions.create")
            : t("actions.update")}
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

      <DeleteCustomComponentDialog
        component={revertOpen ? revertRow : null}
        revert
        onClose={() => setRevertOpen(false)}
        onConfirm={async () => {
          await revert();
          setRevertOpen(false);
        }}
      />
    </Box>
  );
}
