import React, { useState } from "react";
import { Box, Typography } from "@mui/material";
import {
  Description,
  PictureAsPdf,
  InsertDriveFile,
  Article,
} from "@mui/icons-material";
import { useTranslation } from "react-i18next";

const getDocumentIcon = (fileType) => {
  const iconMap = {
    pdf: PictureAsPdf,
    txt: Article,
  };

  const IconComponent = iconMap[fileType?.toLowerCase()] || InsertDriveFile;
  return IconComponent;
};

const getDocumentColor = (fileType) => {
  const colorMap = {
    pdf: "primary.main",
    txt: "primary.main",
  };

  return colorMap[fileType?.toLowerCase()] || "#6B7280";
};

export default function DocumentListItem({
  document,
  disabled = false,
  onClick,
}) {
  const { t } = useTranslation(["generative"]);
  const [isHovered, setIsHovered] = useState(false);

  const DocumentIcon = getDocumentIcon(document.type);
  const documentColor = getDocumentColor(document.type);

  return (
    <Box
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={disabled ? null : onClick}
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1.5,
        p: 1.5,
        width: "100%",
        minWidth: 0,
        maxWidth: "100%",
        bgcolor: disabled ? "rgb(32, 32, 32)" : "rgb(44, 44, 44)",
        border: "1px solid rgb(39, 39, 42)",
        borderRadius: 1,
        cursor: disabled ? "not-allowed" : "pointer",
        transition: "all 0.2s",
        opacity: disabled ? 0.5 : 1,
        filter: disabled ? "grayscale(0.6)" : "none",
        position: "relative",
        "&:hover": {
          bgcolor: disabled ? "rgb(32, 32, 32)" : "rgb(60, 60, 60)",
          borderColor: disabled ? "rgb(39, 39, 42)" : documentColor,
          transform: disabled ? "none" : "translateX(4px)",
        },
        "&::after": disabled
          ? {
              content: '""',
              position: "absolute",
              inset: 0,
              borderRadius: 1,
              pointerEvents: "none",
              background:
                "repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(0, 0, 0, 0.1) 10px, rgba(0, 0, 0, 0.1) 20px)",
            }
          : {},
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          width: 36,
          height: 36,
          borderRadius: 1,
          bgcolor: disabled ? "rgb(50, 50, 50)" : "rgb(63, 63, 70)",
          color: disabled ? "rgb(150, 150, 150)" : "rgb(255, 255, 255)",
          flexShrink: 0,
          transition: "all 0.2s",
        }}
      >
        <DocumentIcon sx={{ fontSize: 20 }} />
      </Box>

      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
            mb: 0.5,
          }}
        >
          <Typography
            variant="body2"
            sx={{
              color: disabled ? "rgb(150, 150, 150)" : "rgb(250, 250, 250)",
              fontWeight: 500,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {document.name}
          </Typography>
        </Box>
        <Typography
          variant="caption"
          sx={{
            color: disabled ? "rgb(90, 90, 90)" : "rgb(113, 113, 122)",
            textTransform: "uppercase",
            fontSize: "0.7rem",
            fontWeight: 600,
          }}
        >
          {document.type || t("generative:rag.documents.table.unknownType")}
        </Typography>
      </Box>
    </Box>
  );
}
