import React from "react";
import { Box, Typography, Tooltip } from "@mui/material";
import StorageIcon from "@mui/icons-material/Storage";
import TagIcon from "@mui/icons-material/Tag";
import DescriptionIcon from "@mui/icons-material/Description";
import InfoIcon from "@mui/icons-material/Info";
import { HeaderBox } from "./HeaderBox";
import { useTranslation } from "react-i18next";

export default function Header({ totalRows, totalColumns, fileSize }) {
  const { t } = useTranslation(["common", "datasets"]);

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 2,
        flexGrow: 1,
        minHeight: 0,
      }}
    >
      <Box
        sx={{
          display: "flex",
          flexDirection: "row",
          gap: 2,
          justifyContent: "flex-start",
          alignItems: "stretch",
          width: "100%",
          flexWrap: "wrap",
          flexGrow: 0,
        }}
      >
        <HeaderBox
          title={t("datasets:label.totalRows")}
          value={totalRows}
          IconComponent={StorageIcon}
          iconColor="rgb(100, 150, 255)"
          bgColor="rgba(100, 150, 255, 0.15)"
        />
        <HeaderBox
          title={t("datasets:label.totalColumns")}
          value={totalColumns}
          IconComponent={TagIcon}
          iconColor="rgb(100, 200, 150)"
          bgColor="rgba(100, 200, 150, 0.15)"
        />
        <HeaderBox
          title={t("datasets:label.fileSizeMB")}
          value={fileSize ? fileSize?.toFixed(3) : "N/A"}
          IconComponent={DescriptionIcon}
          iconColor="rgb(180, 120, 200)"
          bgColor="rgba(180, 120, 200, 0.15)"
        />
      </Box>
    </Box>
  );
}
