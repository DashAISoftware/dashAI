import React from "react";
import { List, ListItem, ListItemText, Chip, Box } from "@mui/material";
import { Transform } from "@mui/icons-material";
import { formatDate } from "../../pages/results/constants/formatDate";
import { formatScope } from "./utils";

export default function ConverterHistoryList({ converters }) {
  return (
    <List>
      {converters.map((converter, index) => {
        const scopeText = converter.parameters?.scope
          ? formatScope(converter.parameters.scope)
          : "";
        return (
          <ListItem
            key={converter.id}
            divider={index < converters.length - 1}
            sx={{ flexDirection: "column", alignItems: "flex-start" }}
          >
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                width: "100%",
              }}
            >
              <Transform sx={{ mr: 2, color: "#00BEBB" }} />
              <ListItemText
                primary={converter.converter}
                secondary={scopeText}
              />
              <Chip label={formatDate(converter.created)} size="small" />
            </Box>
          </ListItem>
        );
      })}
    </List>
  );
}
