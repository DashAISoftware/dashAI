import React from "react";
import { Box, Typography, Tooltip } from "@mui/material";
import StorageIcon from "@mui/icons-material/Storage";
import TagIcon from "@mui/icons-material/Tag";
import DescriptionIcon from "@mui/icons-material/Description";
import InfoIcon from "@mui/icons-material/Info";
import { HeaderBox } from "./HeaderBox";

export default function Header({
  totalRows,
  totalColumns,
  fileSize,
  duplicateRows,
  missingValues,
}) {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 1,
        flexGrow: 1,
        minHeight: 0,
      }}
    >
      <Box
        sx={{
          display: "flex",
          flexDirection: "row",
          gap: 1,
          justifyContent: "flex-start",
          alignItems: "flex-start",
          width: "100%",
          flexWrap: "wrap",
          flexGrow: 0,
        }}
      >
        <HeaderBox
          title="Total Rows"
          value={totalRows}
          IconComponent={StorageIcon}
          iconColor="rgb(100, 150, 255)"
          bgColor="rgba(100, 150, 255, 0.15)"
        />
        <HeaderBox
          title="Total Columns"
          value={totalColumns}
          IconComponent={TagIcon}
          iconColor="rgb(100, 200, 150)"
          bgColor="rgba(100, 200, 150, 0.15)"
        />
        <HeaderBox
          title="File Size (MB)"
          value={fileSize ? fileSize?.toFixed(3) : "N/A"}
          IconComponent={DescriptionIcon}
          iconColor="rgb(180, 120, 200)"
          bgColor="rgba(180, 120, 200, 0.15)"
        />
        <HeaderBox
          title="Duplicate Rows"
          value={duplicateRows ?? "N/A"}
          IconComponent={InfoIcon}
          iconColor="rgb(255, 180, 100)"
          bgColor="rgba(255, 180, 100, 0.15)"
        />
        <HeaderBox
          title="Missing Values"
          value={Object.values(missingValues).reduce((a, b) => a + b, 0)}
          IconComponent={InfoIcon}
          iconColor="rgb(255, 120, 120)"
          bgColor="rgba(255, 120, 120, 0.15)"
        />
      </Box>
    </Box>
  );
}
