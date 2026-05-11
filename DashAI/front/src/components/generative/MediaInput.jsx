import { useState, useRef } from "react";
import { TextField, Button, Box, IconButton } from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import ImageIcon from "@mui/icons-material/Image";
import CloseIcon from "@mui/icons-material/Close";
import { useTranslation } from "react-i18next";

export function MediaInput({
  onSendMessage,
  isLoading = false,
  maxImages = 1,
}) {
  const [text, setText] = useState("");
  const [images, setImages] = useState([]);
  const [previews, setPreviews] = useState([]);
  const fileInputRef = useRef(null);
  const { t } = useTranslation(["generative"]);

  const handleImageChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files);
      const validFiles = newFiles.slice(0, maxImages - images.length);

      if (validFiles.length > 0) {
        // Create preview URLs
        const newPreviews = validFiles.map((file) => URL.createObjectURL(file));

        setImages([...images, ...validFiles]);
        setPreviews([...previews, ...newPreviews]);
      }
    }
  };

  const removeImage = (index) => {
    // Revoke the object URL to avoid memory leaks
    URL.revokeObjectURL(previews[index]);

    const newImages = [...images];
    const newPreviews = [...previews];
    newImages.splice(index, 1);
    newPreviews.splice(index, 1);

    setImages(newImages);
    setPreviews(newPreviews);

    // Reset the file input so the same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSendMessage = () => {
    if (text.trim() && images.length > 0) {
      onSendMessage(images.concat(text));
      setText("");

      // Clean up all preview URLs
      previews.forEach((url) => URL.revokeObjectURL(url));
      setImages([]);
      setPreviews([]);

      // Reset the file input so the same file can be selected again
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        width: "100%",
        gap: 2,
      }}
    >
      {/* Image previews */}
      {previews.length > 0 && (
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
          {previews.map((preview, index) => (
            <Box key={index} sx={{ position: "relative" }}>
              <Box
                component="img"
                src={preview || "/placeholder.svg"}
                alt={`Preview ${index}`}
                sx={{
                  height: 80,
                  width: 80,
                  objectFit: "cover",
                  borderRadius: 1,
                }}
              />
              <IconButton
                size="small"
                onClick={() => removeImage(index)}
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
      )}

      {/* Text input and controls */}
      <Box sx={{ display: "flex", alignItems: "flex-end", gap: 1 }}>
        <TextField
          fullWidth
          multiline
          minRows={3}
          maxRows={6}
          placeholder={t("generative:label.typeYourMessage")}
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={isLoading}
          variant="outlined"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey && !isLoading) {
              e.preventDefault();
              handleSendMessage();
            }
          }}
        />

        <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
          <Box
            component="label"
            htmlFor="image-upload"
            sx={{
              cursor: images.length >= maxImages ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: 40,
              height: 40,
              borderRadius: 1,
              border: 1,
              borderColor: "divider",
              opacity: images.length >= maxImages ? 0.5 : 1,
              "&:hover": {
                bgcolor:
                  images.length >= maxImages ? undefined : "action.hover",
              },
            }}
          >
            <ImageIcon sx={{ fontSize: 20 }} />
          </Box>
          <Box
            component="input"
            id="image-upload"
            type="file"
            accept="image/*"
            multiple
            onChange={handleImageChange}
            disabled={isLoading || images.length >= maxImages}
            sx={{ display: "none" }}
            ref={fileInputRef}
          />

          <Button
            variant="contained"
            color="primary"
            onClick={handleSendMessage}
            disabled={isLoading || !text.trim() || images.length === 0}
            sx={{ minWidth: 40, width: 40, height: 40, padding: 0 }}
          >
            <SendIcon />
          </Button>
        </Box>
      </Box>
    </Box>
  );
}
