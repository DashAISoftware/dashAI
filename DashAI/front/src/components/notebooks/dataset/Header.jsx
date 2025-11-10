import React from "react";
import { Box, Typography } from "@mui/material";
import StorageIcon from "@mui/icons-material/Storage";
import TagIcon from "@mui/icons-material/Tag";
import DescriptionIcon from "@mui/icons-material/Description";
import InfoIcon from "@mui/icons-material/Info";

export default function Header({
  totalRows,
  totalColumns,
  fileSize,
  duplicateRows,
  missingValues,
}) {
  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <Box
        sx={{
          display: "flex",
          flexDirection: "row",
          gap: 1,
          justifyContent: "",
          alignItems: "flex-start",
          height: "120px",
          width: "100%",
          flexWrap: "wrap",
        }}
      >
        <Box
          sx={{
            minWidth: "140px",
            height: "100%",
            flex: 1,
            borderRadius: 2,
            bgcolor: "#2C2C2C",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "flex-start",
            p: 2,
            boxShadow: 3,
          }}
        >
          <StorageIcon
            sx={{
              color: "blue",
              bgcolor: "rgba(0, 0, 255, 0.2)",
              mb: 1,
              borderRadius: 1,
              p: 0.4,
            }}
          />
          <Typography
            variant="body2"
            sx={{
              color: "text.secondary",
              lineHeight: 1.6,
            }}
          >
            Total Rows
          </Typography>
          <Typography variant="h4" align="center">
            {totalRows}
          </Typography>
        </Box>
        <Box
          sx={{
            minWidth: "140px",
            height: "100%",
            flex: 1,
            borderRadius: 2,
            bgcolor: "#2C2C2C",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "flex-start",
            p: 2,
            boxShadow: 3,
          }}
        >
          <TagIcon
            sx={{
              color: "green",
              bgcolor: "rgba(0, 128, 0, 0.2)",
              mb: 1,
              borderRadius: 1,
              p: 0.4,
            }}
          />
          <Typography
            variant="body2"
            sx={{
              color: "text.secondary",
              lineHeight: 1.6,
            }}
          >
            Total Columns
          </Typography>
          <Typography variant="h4" align="center">
            {totalColumns}
          </Typography>
        </Box>
        <Box
          sx={{
            minWidth: "140px",
            height: "100%",
            flex: 1,
            borderRadius: 2,
            bgcolor: "#2C2C2C",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "flex-start",
            p: 2,
            boxShadow: 3,
          }}
        >
          <DescriptionIcon
            sx={{
              color: "purple",
              bgcolor: "rgba(128, 0, 128, 0.2)",
              mb: 1,
              borderRadius: 1,
              p: 0.4,
            }}
          />
          <Typography
            variant="body2"
            sx={{
              color: "text.secondary",
              lineHeight: 1.6,
            }}
          >
            File Size
          </Typography>
          <Typography variant="h4" align="center">
            {fileSize?.toFixed(3)} MB
          </Typography>
        </Box>
        <Box
          sx={{
            minWidth: "140px",
            height: "100%",
            flex: 1,
            borderRadius: 2,
            bgcolor: "#2C2C2C",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "flex-start",
            p: 2,
            boxShadow: 3,
          }}
        >
          <InfoIcon
            sx={{
              color: "orange",
              bgcolor: "rgba(255, 165, 0, 0.2)",
              mb: 1,
              borderRadius: 1,
              p: 0.4,
            }}
          />
          <Typography
            variant="body2"
            sx={{
              color: "text.secondary",
              lineHeight: 1.6,
            }}
          >
            Missing Values
          </Typography>
          <Typography variant="h4" align="center">
            {Object.values(missingValues ?? {}).reduce((a, b) => a + b, 0)}
          </Typography>
        </Box>
      </Box>
    </Box>
  );
}
