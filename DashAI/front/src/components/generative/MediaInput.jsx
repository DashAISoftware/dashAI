import { useState, useRef, useMemo } from "react";
import {
  TextField,
  Button,
  Box,
  IconButton,
  Popper,
  Fade,
  ClickAwayListener,
  Stack,
  Tooltip,
  Paper,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import ImageIcon from "@mui/icons-material/Image";
import AudiotrackIcon from "@mui/icons-material/Audiotrack";
import VideocamIcon from "@mui/icons-material/Videocam";
import AttachFileIcon from "@mui/icons-material/AttachFile";
import CloseIcon from "@mui/icons-material/Close";
import { useTranslation } from "react-i18next";

const MEDIA_KINDS = {
  Image: {
    accept: "image/*",
    icon: ImageIcon,
    tooltipKey: "label.attachImage",
  },
  Audio: {
    accept: "audio/*",
    icon: AudiotrackIcon,
    tooltipKey: "label.attachAudio",
  },
  Video: {
    accept: "video/*",
    icon: VideocamIcon,
    tooltipKey: "label.attachVideo",
  },
};

const MEDIA_ORDER = Object.keys(MEDIA_KINDS);

// Normalize cardinality entries into {min, max}.
// Accepts:
//   - integer N → exactly N
//   - "n"       → 0..Infinity
//   - {min, max} → as-is, max "n" means Infinity
const parseCardinality = (value) => {
  if (value === "n") return { min: 0, max: Infinity };
  if (typeof value === "number") return { min: value, max: value };
  if (value && typeof value === "object") {
    const min = Number(value.min ?? 0);
    const rawMax = value.max ?? "n";
    const max = rawMax === "n" ? Infinity : Number(rawMax);
    return { min, max };
  }
  return { min: 0, max: 0 };
};

const isActive = (value) => {
  const { min, max } = parseCardinality(value);
  return max > 0 || min > 0;
};

export function MediaInput({
  onSendMessage,
  isLoading = false,
  inputsCardinality = { str: 1 },
}) {
  const [text, setText] = useState("");
  const [filesByKind, setFilesByKind] = useState({});
  const [previewsByKind, setPreviewsByKind] = useState({});
  const [menuOpen, setMenuOpen] = useState(false);
  const attachBtnRef = useRef(null);
  const fileInputRefs = useRef({});
  const { t } = useTranslation(["generative"]);

  const textCard = parseCardinality(inputsCardinality.str);
  const wantsText = textCard.max > 0;
  const textRequired = textCard.min > 0;
  const activeKinds = useMemo(
    () => MEDIA_ORDER.filter((kind) => isActive(inputsCardinality[kind])),
    [inputsCardinality],
  );
  const hasAnyMedia = activeKinds.length > 0;

  const handleFileChange = (kind) => (e) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const { max } = parseCardinality(inputsCardinality[kind]);
    const current = filesByKind[kind] || [];
    const remaining = max - current.length;
    if (remaining <= 0) return;

    const incoming = Array.from(e.target.files).slice(0, remaining);
    const newPreviews = incoming.map((f) => URL.createObjectURL(f));

    setFilesByKind({ ...filesByKind, [kind]: [...current, ...incoming] });
    setPreviewsByKind({
      ...previewsByKind,
      [kind]: [...(previewsByKind[kind] || []), ...newPreviews],
    });
  };

  const removeFile = (kind, index) => {
    URL.revokeObjectURL(previewsByKind[kind][index]);
    const newFiles = [...(filesByKind[kind] || [])];
    const newPreviews = [...(previewsByKind[kind] || [])];
    newFiles.splice(index, 1);
    newPreviews.splice(index, 1);
    setFilesByKind({ ...filesByKind, [kind]: newFiles });
    setPreviewsByKind({ ...previewsByKind, [kind]: newPreviews });
    if (fileInputRefs.current[kind]) {
      fileInputRefs.current[kind].value = "";
    }
  };

  const requirementsMet = useMemo(() => {
    if (textRequired && !text.trim()) return false;
    for (const kind of activeKinds) {
      const { min, max } = parseCardinality(inputsCardinality[kind]);
      const count = (filesByKind[kind] || []).length;
      if (count < min || count > max) return false;
    }
    return true;
  }, [textRequired, text, activeKinds, filesByKind, inputsCardinality]);

  const handleSend = () => {
    if (!requirementsMet) return;
    const allFiles = activeKinds.flatMap((kind) => filesByKind[kind] || []);
    const payload = wantsText ? [...allFiles, text] : allFiles;
    onSendMessage(payload);

    setText("");
    Object.values(previewsByKind).forEach((arr) =>
      arr.forEach((url) => URL.revokeObjectURL(url)),
    );
    setFilesByKind({});
    setPreviewsByKind({});
    Object.values(fileInputRefs.current).forEach((ref) => {
      if (ref) ref.value = "";
    });
  };

  const pickKind = (kind) => {
    setMenuOpen(false);
    fileInputRefs.current[kind]?.click();
  };

  return (
    <Box
      sx={{ display: "flex", flexDirection: "column", width: "100%", gap: 2 }}
    >
      {activeKinds.map((kind) => {
        const previews = previewsByKind[kind] || [];
        if (previews.length === 0) return null;
        const isImage = kind === "Image";
        return (
          <Box
            key={`previews-${kind}`}
            sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}
          >
            {previews.map((preview, index) => (
              <Box key={`${kind}-${index}`} sx={{ position: "relative" }}>
                {isImage ? (
                  <Box
                    component="img"
                    src={preview}
                    alt={`${kind} preview ${index}`}
                    sx={{
                      height: 80,
                      width: 80,
                      objectFit: "cover",
                      borderRadius: 1,
                    }}
                  />
                ) : (
                  <Box
                    sx={{
                      height: 80,
                      minWidth: 80,
                      px: 1,
                      borderRadius: 1,
                      border: 1,
                      borderColor: "divider",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "0.75rem",
                    }}
                  >
                    {kind} #{index + 1}
                  </Box>
                )}
                <IconButton
                  size="small"
                  onClick={() => removeFile(kind, index)}
                  sx={{
                    position: "absolute",
                    top: -8,
                    right: -8,
                    bgcolor: "error.main",
                    color: "white",
                    padding: "4px",
                    "&:hover": { bgcolor: "error.dark" },
                  }}
                >
                  <CloseIcon sx={{ fontSize: 14 }} />
                </IconButton>
              </Box>
            ))}
          </Box>
        );
      })}

      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        {wantsText && (
          <TextField
            fullWidth
            multiline={hasAnyMedia}
            minRows={hasAnyMedia ? 3 : 1}
            maxRows={hasAnyMedia ? 3 : 1}
            placeholder={t("generative:label.typeYourMessage")}
            label={
              !hasAnyMedia ? t("generative:label.typeYourMessage") : undefined
            }
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={isLoading}
            variant="outlined"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && !isLoading) {
                e.preventDefault();
                handleSend();
              }
            }}
            data-tour="chat-input"
          />
        )}

        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            gap: 1,
            alignItems: "center",
            position: "relative",
          }}
        >
          <IconButton
            ref={attachBtnRef}
            onClick={() => hasAnyMedia && !isLoading && setMenuOpen((v) => !v)}
            disabled={isLoading || !hasAnyMedia}
            sx={(theme) => {
              const isDark = theme.palette.mode === "dark";
              const bg = isDark
                ? theme.palette.grey[800]
                : theme.palette.grey[300];
              const fg = isDark
                ? theme.palette.grey[100]
                : theme.palette.grey[800];
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
            {menuOpen ? <CloseIcon /> : <AttachFileIcon />}
          </IconButton>

          <Popper
            open={menuOpen}
            anchorEl={attachBtnRef.current}
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
                  <ClickAwayListener onClickAway={() => setMenuOpen(false)}>
                    <Stack direction="column" spacing={1.25}>
                      {MEDIA_ORDER.map((kind) => {
                        const { icon: Icon, tooltipKey } = MEDIA_KINDS[kind];
                        const enabled = isActive(inputsCardinality[kind]);
                        const { min, max } = parseCardinality(
                          inputsCardinality[kind],
                        );
                        const current = (filesByKind[kind] || []).length;
                        const reachedLimit = enabled && current >= max;
                        const disabled = !enabled || reachedLimit;
                        const label = t(`generative:${tooltipKey}`, kind);
                        const maxLabel = max === Infinity ? "∞" : max;
                        const rangeLabel =
                          min === max
                            ? `exactly ${min}`
                            : max === Infinity
                              ? `min ${min}, max ∞`
                              : `min ${min}, max ${max}`;
                        const tooltipText = !enabled
                          ? `${label} (not supported)`
                          : `${label} — ${current}/${maxLabel} (${rangeLabel})`;
                        return (
                          <Tooltip
                            key={`action-${kind}`}
                            title={tooltipText}
                            placement="left"
                            arrow
                          >
                            <span>
                              <IconButton
                                onClick={() => pickKind(kind)}
                                disabled={disabled}
                                sx={(theme) => {
                                  const isDark = theme.palette.mode === "dark";
                                  const bg = isDark
                                    ? theme.palette.grey[700]
                                    : theme.palette.grey[200];
                                  const fg = isDark
                                    ? theme.palette.grey[100]
                                    : theme.palette.grey[800];
                                  const disabledBg =
                                    theme.palette.ui?.disabled ??
                                    theme.palette.action.disabledBackground;
                                  const borderColor =
                                    theme.palette.ui?.border ??
                                    theme.palette.divider;
                                  return {
                                    width: 40,
                                    height: 40,
                                    borderRadius: 1,
                                    color: fg,
                                    backgroundColor: bg,
                                    "&:hover": { backgroundColor: bg },
                                    "&.Mui-disabled": {
                                      position: "relative",
                                      overflow: "hidden",
                                      color: theme.palette.text.disabled,
                                      backgroundColor: disabledBg,
                                      border: `1px solid ${borderColor}`,
                                      opacity: 0.6,
                                      filter: "grayscale(0.6)",
                                      cursor: "not-allowed",
                                    },
                                    "&.Mui-disabled::after": {
                                      content: '""',
                                      position: "absolute",
                                      inset: 0,
                                      borderRadius: 1,
                                      pointerEvents: "none",
                                      background:
                                        "repeating-linear-gradient(45deg, transparent, transparent 6px, rgba(0,0,0,0.12) 6px, rgba(0,0,0,0.12) 12px)",
                                    },
                                  };
                                }}
                              >
                                <Icon fontSize="small" />
                              </IconButton>
                            </span>
                          </Tooltip>
                        );
                      })}
                    </Stack>
                  </ClickAwayListener>
                </Paper>
              </Fade>
            )}
          </Popper>

          {MEDIA_ORDER.map((kind) => {
            const { accept } = MEDIA_KINDS[kind];
            const { max } = parseCardinality(inputsCardinality[kind]);
            return (
              <Box
                key={`file-input-${kind}`}
                component="input"
                type="file"
                accept={accept}
                multiple={max > 1}
                onChange={handleFileChange(kind)}
                disabled={isLoading}
                sx={{ display: "none" }}
                ref={(el) => {
                  fileInputRefs.current[kind] = el;
                }}
              />
            );
          })}

          <Button
            variant="contained"
            color="primary"
            onClick={handleSend}
            disabled={isLoading || !requirementsMet}
            sx={{ minWidth: 40, width: 40, height: 40, padding: 0 }}
          >
            <SendIcon />
          </Button>
        </Box>
      </Box>
    </Box>
  );
}
