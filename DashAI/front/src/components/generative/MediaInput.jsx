import { useState, useRef, useMemo } from "react";
import { TextField, Button, Box, IconButton, Tooltip } from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import ImageIcon from "@mui/icons-material/Image";
import AudiotrackIcon from "@mui/icons-material/Audiotrack";
import VideocamIcon from "@mui/icons-material/Videocam";
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

const limitFor = (cardinality) =>
  cardinality === "n" ? Infinity : Number(cardinality) || 0;

export function MediaInput({
  onSendMessage,
  isLoading = false,
  inputsCardinality = { str: 1 },
}) {
  const [text, setText] = useState("");
  const [filesByKind, setFilesByKind] = useState({});
  const [previewsByKind, setPreviewsByKind] = useState({});
  const fileInputRefs = useRef({});
  const { t } = useTranslation(["generative"]);

  const wantsText = (inputsCardinality.str ?? 0) !== 0;
  const mediaKinds = useMemo(
    () =>
      Object.keys(MEDIA_KINDS).filter(
        (kind) => (inputsCardinality[kind] ?? 0) !== 0,
      ),
    [inputsCardinality],
  );

  const handleFileChange = (kind) => (e) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const limit = limitFor(inputsCardinality[kind]);
    const current = filesByKind[kind] || [];
    const remaining = limit - current.length;
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
    if (wantsText && !text.trim()) return false;
    for (const kind of mediaKinds) {
      const card = inputsCardinality[kind];
      const count = (filesByKind[kind] || []).length;
      if (card === "n") {
        if (count === 0) return false;
      } else if (count !== Number(card)) {
        return false;
      }
    }
    return true;
  }, [wantsText, text, mediaKinds, filesByKind, inputsCardinality]);

  const handleSend = () => {
    if (!requirementsMet) return;
    const allFiles = mediaKinds.flatMap((kind) => filesByKind[kind] || []);
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

  return (
    <Box
      sx={{ display: "flex", flexDirection: "column", width: "100%", gap: 2 }}
    >
      {mediaKinds.map((kind) => {
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
            multiline={mediaKinds.length > 0}
            minRows={mediaKinds.length > 0 ? 3 : 1}
            maxRows={mediaKinds.length > 0 ? 3 : 1}
            placeholder={t("generative:label.typeYourMessage")}
            label={
              mediaKinds.length === 0
                ? t("generative:label.typeYourMessage")
                : undefined
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

        <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
          {mediaKinds.map((kind) => {
            const { accept, icon: Icon, tooltipKey } = MEDIA_KINDS[kind];
            const limit = limitFor(inputsCardinality[kind]);
            const current = (filesByKind[kind] || []).length;
            const reachedLimit = current >= limit;
            const inputId = `media-upload-${kind}`;
            return (
              <Box key={`attach-${kind}`}>
                <Tooltip title={t(`generative:${tooltipKey}`, kind)}>
                  <Box
                    component="label"
                    htmlFor={inputId}
                    sx={{
                      cursor: reachedLimit ? "not-allowed" : "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      width: 40,
                      height: 40,
                      borderRadius: 1,
                      border: 1,
                      borderColor: "divider",
                      opacity: reachedLimit ? 0.5 : 1,
                      "&:hover": {
                        bgcolor: reachedLimit ? undefined : "action.hover",
                      },
                    }}
                  >
                    <Icon sx={{ fontSize: 20 }} />
                  </Box>
                </Tooltip>
                <Box
                  component="input"
                  id={inputId}
                  type="file"
                  accept={accept}
                  multiple={limit > 1}
                  onChange={handleFileChange(kind)}
                  disabled={isLoading || reachedLimit}
                  sx={{ display: "none" }}
                  ref={(el) => {
                    fileInputRefs.current[kind] = el;
                  }}
                />
              </Box>
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
