import { useRef } from "react";
import {
  IconButton,
  Popper,
  Fade,
  ClickAwayListener,
  Stack,
  Paper,
} from "@mui/material";
import AttachFileIcon from "@mui/icons-material/AttachFile";
import CloseIcon from "@mui/icons-material/Close";
import { useTranslation } from "react-i18next";
import {
  MEDIA_KINDS,
  MEDIA_ORDER,
  parseCardinality,
  isActive,
  kindTooltip,
} from "./constants";
import { MediaKindButton } from "./MediaKindButton";

export function MediaAttachPopper({
  open,
  setOpen,
  disabled,
  inputsCardinality,
  filesByKind,
  onPick,
}) {
  const anchorRef = useRef(null);
  const { t } = useTranslation(["generative"]);

  return (
    <>
      <IconButton
        ref={anchorRef}
        onClick={() => !disabled && setOpen((v) => !v)}
        disabled={disabled}
        sx={(theme) => {
          const isDark = theme.palette.mode === "dark";
          const bg = isDark ? theme.palette.grey[800] : theme.palette.grey[300];
          const fg = isDark ? theme.palette.grey[100] : theme.palette.grey[800];
          return {
            width: 40,
            height: 40,
            borderRadius: 1,
            color: fg,
            backgroundColor: bg,
            "&:hover": { backgroundColor: bg },
            "&.Mui-disabled": {
              color: theme.palette.text.disabled,
              backgroundColor: bg,
              opacity: 0.6,
            },
          };
        }}
      >
        {open ? <CloseIcon /> : <AttachFileIcon />}
      </IconButton>
      <Popper
        open={open}
        anchorEl={anchorRef.current}
        placement="top-end"
        transition
        modifiers={[{ name: "offset", options: { offset: [0, 8] } }]}
        sx={{ zIndex: 1200 }}
      >
        {({ TransitionProps }) => (
          <Fade {...TransitionProps} timeout={200}>
            <Paper
              elevation={0}
              sx={{
                p: 0,
                backgroundColor: "transparent",
                boxShadow: "none",
              }}
            >
              <ClickAwayListener onClickAway={() => setOpen(false)}>
                <Stack direction="column" spacing={1.25}>
                  {MEDIA_ORDER.map((kind) => {
                    const { icon, tooltipKey } = MEDIA_KINDS[kind];
                    const enabled = isActive(inputsCardinality[kind]);
                    const range = parseCardinality(inputsCardinality[kind]);
                    const count = (filesByKind[kind] || []).length;
                    const kindDisabled =
                      !enabled || (enabled && count >= range.max);
                    const label = t(`generative:${tooltipKey}`, kind);
                    return (
                      <MediaKindButton
                        key={`action-${kind}`}
                        icon={icon}
                        tooltip={kindTooltip(label, enabled, count, range)}
                        tooltipPlacement="left"
                        disabled={kindDisabled}
                        onClick={() => onPick(kind)}
                      />
                    );
                  })}
                </Stack>
              </ClickAwayListener>
            </Paper>
          </Fade>
        )}
      </Popper>
    </>
  );
}
