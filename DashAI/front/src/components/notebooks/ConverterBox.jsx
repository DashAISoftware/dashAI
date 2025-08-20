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
import { getConverterStatus } from "../../utils/converterStatus";
import { getComponentById } from "../../api/component";
import { getConverterById } from "../../api/converter";

export default function ConverterBox({ converter, height = "320px" }) {
  const [converterComponent, setConverterComponent] = useState({});
  const [converterState, setConverterState] = useState(converter);

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
  }, []);

  useEffect(() => {
    let intervalId;

    const fetchConverterStatus = async () => {
      try {
        const updatedConverter = await getConverterById(converter.id);
        setConverterState(updatedConverter);

        const status = getConverterStatus(updatedConverter.status);
        if (status === "Finished" || status === "Error") {
          clearInterval(intervalId); // stop polling
        }
      } catch (error) {
        console.error("Failed to fetch converter status:", error);
        clearInterval(intervalId); // stop polling on error
      }
    };

    // only start polling if the status is not Finished or Error
    const currentStatus = getConverterStatus(converterState.status);
    if (currentStatus !== "Finished" && currentStatus !== "Error") {
      intervalId = setInterval(fetchConverterStatus, 1500); // polling every 1.5s
    }

    return () => clearInterval(intervalId);
  }, [converter.id, converterState.status]);

  const statusLabel = getConverterStatus(converterState.status);

  return (
    <Card
      key={converter.id}
      sx={{ bgcolor: "#212121", borderRadius: 2, height: height }}
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
            <Typography variant="h6">{converterState.converter}</Typography>
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
            {converterState.parameters && (
              <DataGrid
                rows={[
                  {
                    id: 2,
                    key: "Target Index",
                    value: converterState.parameters.target_index,
                  },
                  {
                    id: 3,
                    key: "Scope - Columns",
                    value:
                      converterState.parameters.scope?.columns?.length === 0
                        ? "All"
                        : converterState.parameters.scope.columns.join(", "),
                  },
                  {
                    id: 4,
                    key: "Scope - Rows",
                    value:
                      converterState.parameters.scope.rows.length === 0
                        ? "All"
                        : converterState.parameters.scope.rows.join(", "),
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
