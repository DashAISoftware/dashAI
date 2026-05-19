import React from "react";
import { Alert, Box, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";

const ItemsToDeleteList = React.memo(function ItemsToDeleteList({ items }) {
  if (!items || items.length === 0) return null;

  const { t } = useTranslation(["common", "datasets"]);

  return (
    <Alert severity="error" icon={false} sx={{ mt: 2 }}>
      <Typography variant="subtitle2" sx={{ color: "error.main", mb: 1 }}>
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
                py: 0.5,
                fontWeight: isSelected ? "bold" : "normal",
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
    </Alert>
  );
});

export default ItemsToDeleteList;
