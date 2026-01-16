import React, { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  Box,
  Typography,
  Chip,
  CircularProgress,
  IconButton,
} from "@mui/material";
import { Delete } from "@mui/icons-material";
import { DataGrid } from "@mui/x-data-grid";
import Transform from "@mui/icons-material/Transform";
import { getConverterStatus } from "../../../utils/converterStatus";
import { getComponentById } from "../../../api/component";
import { getConverterById } from "../../../api/converter";
import { useTranslation } from "react-i18next";

export default function ConverterBox({
  converter,
  onStatusChange,
  handleConverterDeleteClick,
}) {
  const [converterComponent, setConverterComponent] = useState({});
  const { t } = useTranslation(["common", "datasets"]);

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

        if (updatedConverter.status !== converter.status) {
          onStatusChange(updatedConverter.id, updatedConverter.status);
        }

        const status = updatedConverter.status;
        if (status === 3 || status === 4) {
          // Finished or Error
          clearInterval(intervalId);
        }
      } catch (error) {
        console.error("Failed to fetch converter status:", error);
        clearInterval(intervalId);
      }
    };

    const currentStatus = converter.status;
    if (currentStatus !== 3 && currentStatus !== 4) {
      //  Not Finished and not Error
      intervalId = setInterval(fetchConverterStatus, 1500);
    }

    return () => clearInterval(intervalId);
  }, [converter.id, converter.status, onStatusChange]);

  const statusLabel = converter.status;

  return (
    <Card
      key={converter.id}
      className="converter-box"
      sx={{ bgcolor: "#212121", borderRadius: 2, height: "100%" }}
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
            <Typography variant="h6">
              {converterComponent.display_name}
            </Typography>
          </Box>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Chip
              label={getConverterStatus(statusLabel, t)}
              color={statusLabel === 3 ? "primary" : "default"} // Finished
              size="small"
            />
            {(statusLabel === 4 || statusLabel === 3) && ( // Error or Finished
              <IconButton
                size="small"
                onClick={() => handleConverterDeleteClick(converter)}
                sx={{
                  width: 24,
                  height: 24,
                  bgcolor: "error.main",
                  "&:hover": { bgcolor: "error.dark" },
                }}
              >
                <Delete sx={{ fontSize: 16 }} />
              </IconButton>
            )}
          </Box>
        </Box>

        {statusLabel === 3 ? ( // Finished
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
                    key: t("datasets:label.targetColumn"),
                    value: converter.parameters.target?.columnName,
                  },
                  {
                    id: 3,
                    key: t("datasets:label.scopeColumns"),
                    value:
                      converter.parameters.scope?.columns?.length === 0
                        ? "All"
                        : converter.parameters.scope.columns
                            .map((col) => col.columnName)
                            .join(", "),
                  },
                  {
                    id: 4,
                    key: t("datasets:label.scopeRows"),
                    value:
                      converter.parameters.scope.rows.length === 0
                        ? "All"
                        : converter.parameters.scope.rows.join(", "),
                  },
                ]}
                columns={[
                  { field: "key", headerName: t("common:parameter"), flex: 1 },
                  { field: "value", headerName: t("common:value"), flex: 4 },
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
                    overflowX: "auto",
                  },
                  "& .MuiDataGrid-cell": {
                    whiteSpace: "nowrap", // keep everything on one line
                  },
                }}
              />
            )}
          </Box>
        ) : statusLabel === 4 ? ( // Error
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
              {t("datasets:error.converterFailed")}
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
            <Typography>{t("common:processing")}</Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}
