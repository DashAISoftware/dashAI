import React from "react";
import {
  List,
  ListItem,
  ListItemText,
  Chip,
  Box,
  IconButton,
} from "@mui/material";
import { Transform, Delete } from "@mui/icons-material";
import { formatDate } from "../../../pages/results/constants/formatDate";
import { formatScope } from "../utils";

export default function ConverterHistoryList({
  converters,
  onConverterDelete,
  showDeleteButtons = false,
}) {
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
              <Transform color="primary" sx={{ mr: 2 }} />
              <ListItemText
                primary={converter.converter}
                secondary={scopeText}
              />
              <Chip label={formatDate(converter.created)} size="small" />
              <IconButton
                onClick={() => onConverterDelete(converter)}
                size="small"
                sx={{ ml: 1 }}
                color="error"
              >
                <Delete />
              </IconButton>
            </Box>
          </ListItem>
        );
      })}
    </List>
  );
}
