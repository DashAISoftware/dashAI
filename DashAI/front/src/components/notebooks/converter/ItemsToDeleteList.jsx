import React from "react";
import { Box, Typography } from "@mui/material";

const ItemsToDeleteList = React.memo(function ItemsToDeleteList({ items }) {
  if (!items || items.length === 0) return null;

  return (
    <Box
      sx={{
        mt: 2,
        p: 2,
        bgcolor: "#2e3037",
        borderRadius: 1,
        border: "1px solid rgba(255, 255, 255, 0.1)",
      }}
    >
      <Typography variant="subtitle2" sx={{ color: "#00BEBB", mb: 1 }}>
        The following items will be deleted:
      </Typography>
      <Box sx={{ maxHeight: 200, overflow: "auto" }}>
        {items.map((item, index) => {
          const itemName =
            item.type === "converter" ? item.converter : item.exploration_type;
          const itemType = item.type === "converter" ? "Converter" : "Explorer";
          const isSelected = index === 0;

          return (
            <Box
              key={`${item.type}-${item.id}`}
              sx={{
                display: "flex",
                alignItems: "center",
                py: 0.5,
                fontWeight: isSelected ? "bold" : "normal",
                //color: isSelected ? "#00BEBB" : "text.secondary",
              }}
            >
              <Typography variant="body2">
                {index + 1}. {itemType}: {itemName}
                {isSelected && " (Selected)"}
              </Typography>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
});

export default ItemsToDeleteList;
