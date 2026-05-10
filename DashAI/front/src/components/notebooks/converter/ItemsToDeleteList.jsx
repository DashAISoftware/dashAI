import React from "react";
import { Box, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";

const ItemsToDeleteList = React.memo(function ItemsToDeleteList({ items }) {
  if (!items || items.length === 0) return null;

  const { t } = useTranslation(["common", "datasets"]);

  return (
    <Box
      sx={{
        mt: 4,
        p: 4,
        bgcolor: "#2e3037",
        borderRadius: 1,
        border: "1px solid rgba(255, 255, 255, 0.1)",
      }}
    >
      <Typography variant="subtitle2" sx={{ color: "error.main", mb: 2 }}>
        {t("common:itemsToBeDeleted")}
      </Typography>
      <Box sx={{ maxHeight: 200, overflow: "auto" }}>
        {items.map((item, index) => {
          const itemName =
            item.type === "converter" ? item.converter : item.exploration_type;
          const itemType =
            item.type === "converter"
              ? t("datasets:label.converter")
              : t("datasets:label.explorer");
          const isSelected = index === 0;

          return (
            <Box
              key={`${item.type}-${item.id}`}
              sx={{
                display: "flex",
                alignItems: "center",
                py: 1,
                fontWeight: isSelected ? "bold" : "normal",
                //color: isSelected ? "#00BEBB" : "text.secondary",
              }}
            >
              <Typography variant="body2">
                {index + 1}. {itemType}: {itemName}
                {isSelected && <span> ({t("common:selected")})</span>}
              </Typography>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
});

export default ItemsToDeleteList;
