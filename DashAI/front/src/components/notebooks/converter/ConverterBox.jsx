import React, { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  Box,
  Typography,
  Chip,
  CircularProgress,
} from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import Transform from "@mui/icons-material/Transform";
import { getConverterStatus } from "../../../utils/converterStatus";
import { getComponentById } from "../../../api/component";
import { getConverterById } from "../../../api/converter";

export default function ConverterBox({
  converter,
  height = "320px",
  onStatusChange,
}) {
  const [converterComponent, setConverterComponent] = useState({});

  useEffect(() => {
    const fetchConverterComponent = async () => {
      try {
        const component = await getComponentById(converter.converter);
        setConverterComponent(component);
      } catch (error) {
        console.error("Failed to fetch converter component:", error);
      }
    };

    fetchConverterComponent();
  }, [converter.converter]);

  useEffect(() => {
    let intervalId;

    const fetchConverterStatus = async () => {
      try {
        const updatedConverter = await getConverterById(converter.id);

        // 🔑 notificar al padre si cambia el estado
        if (updatedConverter.status !== converter.status) {
          onStatusChange(updatedConverter.id, updatedConverter.status);
        }

        const status = getConverterStatus(updatedConverter.status);
        if (status === "Finished" || status === "Error") {
          clearInterval(intervalId);
        }
      } catch (error) {
        console.error("Failed to fetch converter status:", error);
        clearInterval(intervalId);
      }
    };

    const currentStatus = getConverterStatus(converter.status);
    if (currentStatus !== "Finished" && currentStatus !== "Error") {
      intervalId = setInterval(fetchConverterStatus, 1500);
    }

    return () => clearInterval(intervalId);
  }, [converter.id, converter.status, onStatusChange]);

  const statusLabel = getConverterStatus(converter.status);

  return (
    <Card
      key={converter.id}
      sx={{ bgcolor: "#212121", borderRadius: 2, height }}
    >
      <CardContent
        sx={{
          display: "flex",
          flexDirection: "column",
          height: "100%",
        }}
      >
        {/* Header */}
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            mb: 2,
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Transform sx={{ color: "#00BEBB", fontSize: 20 }} />
            <Typography variant="h6">{converter.converter}</Typography>
          </Box>
          <Chip
            label={statusLabel}
            color={statusLabel === "Finished" ? "primary" : "default"}
            size="small"
          />
        </Box>

        {statusLabel === "Finished" ? (
          <Box
            sx={{
              flexGrow: 1,
              bgcolor: "#2e3037",
              borderRadius: 1,
              display: "flex",
              flexDirection: "column",
              p: 2,
              overflow: "hidden",
            }}
          >
            {/* Descripción */}
            <Typography variant="body2" sx={{ color: "text.secondary", mb: 2 }}>
              {converterComponent.description}
            </Typography>

            {/* Parámetros en tabla */}
            {converter.parameters && (
              <DataGrid
                rows={[
                  {
                    id: 2,
                    key: "Target Column",
                    value: converter.parameters.target?.columnName,
                  },
                  {
                    id: 3,
                    key: "Scope - Columns",
                    value:
                      converter.parameters.scope?.columns?.length === 0
                        ? "All"
                        : converter.parameters.scope.columns
                            .map((col) => col.columnName)
                            .join(", "),
                  },
                  {
                    id: 4,
                    key: "Scope - Rows",
                    value:
                      converter.parameters.scope.rows.length === 0
                        ? "All"
                        : converter.parameters.scope.rows.join(", "),
                  },
                ]}
                columns={[
                  { field: "key", headerName: "Parameter", flex: 1 },
                  { field: "value", headerName: "Value", flex: 2 },
                ]}
                hideFooter
                disableColumnMenu
                disableColumnFilter
                disableColumnSelector
                density="compact"
                sx={{
                  height: "100%",
                  width: "100%",
                  "& .MuiDataGrid-virtualScroller": {
                    "&::-webkit-scrollbar": {
                      width: "0px",
                      height: "0px",
                    },
                  },
                }}
              />
            )}
          </Box>
        ) : statusLabel === "Error" ? (
          <Box
            sx={{
              flexGrow: 1,
              bgcolor: "#2e3037",
              borderRadius: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              p: 2,
            }}
          >
            <Typography
              variant="body2"
              sx={{ color: "error.main", textAlign: "center" }}
            >
              An error occurred during processing.
            </Typography>
          </Box>
        ) : (
          <Box
            sx={{
              flexGrow: 1,
              bgcolor: "rgba(255, 255, 255, 0.05)",
              borderRadius: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <CircularProgress size={20} sx={{ mr: 1 }} />
            <Typography>Processing...</Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}
