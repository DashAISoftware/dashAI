import { Box, IconButton } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";

export function MediaPreviewList({ activeKinds, previewsByKind, onRemove }) {
  return activeKinds.map((kind) => {
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
              onClick={() => onRemove(kind, index)}
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
  });
}
