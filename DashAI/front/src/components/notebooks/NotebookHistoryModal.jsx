import React, { useEffect, useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  List,
  ListItem,
  ListItemText,
  Chip,
  Box,
  Typography,
  IconButton,
} from "@mui/material";
import { Close, Transform } from "@mui/icons-material";
import { getConvertersByNotebookId } from "../../api/notebook";
import { formatDate } from "../../pages/results/constants/formatDate";

export function NotebookHistoryModal({ open, onClose, notebook }) {
  if (!notebook) return null;

  const [converters, setConverters] = useState([]);

  useEffect(() => {
    const fetchConverters = async () => {
      const response = await getConvertersByNotebookId(notebook.id);
      setConverters(response);
    };

    try {
      fetchConverters();
    } catch (error) {
      console.error("Error fetching converters:", error);
    }
  }, [notebook]);

  const formatScope = (scope) => {
    const cols = scope.columns?.length ? scope.columns.join(", ") : "All";
    const rows = scope.rows?.length ? scope.rows.join(", ") : "All";
    return `Columns: ${cols} | Rows: ${rows}`;
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        Notebook History: {notebook.name}
        <IconButton
          onClick={onClose}
          sx={{ position: "absolute", right: 8, top: 8 }}
        >
          <Close />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 1 }}>
          {converters.length === 0 ? (
            <Typography
              variant="body2"
              color="text.secondary"
              textAlign="center"
              sx={{ py: 4 }}
            >
              No transformations applied yet.
            </Typography>
          ) : (
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
                      <Chip
                        label={formatDate(converter.created)}
                        size="small"
                      />
                    </Box>
                  </ListItem>
                );
              })}
            </List>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}
