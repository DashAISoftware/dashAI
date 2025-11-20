import React, { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  Box,
  Typography,
  Chip,
  IconButton,
  CircularProgress,
} from "@mui/material";
import { Analytics, Info, Delete } from "@mui/icons-material";
import { TabResults } from "./tabs";
import { getExplorerStatus } from "../../../utils/explorerStatus";
import { getComponentById } from "../../../api/component";
import { getExplorerById } from "../../../api/explorer";

export default function ExplorerBox({
  explorer,
  handleExplorerDetailsClick,
  handleExplorerDeleteClick,
  onStatusChange,
}) {
  const [explorerComponent, setExplorerComponent] = useState({});

  useEffect(() => {
    const fetchConverterComponent = async () => {
      try {
        const component = await getComponentById(explorer.exploration_type);
        setExplorerComponent(component);
      } catch (error) {
        console.error("Failed to fetch converter component:", error);
      }
    };

    fetchConverterComponent();
  }, [explorer.exploration_type]);

  useEffect(() => {
    let intervalId;

    const fetchExplorerStatus = async () => {
      try {
        const updatedExplorer = await getExplorerById(explorer.id);

        // 🔑 Notificar al padre si cambia el estado
        if (updatedExplorer.status !== explorer.status) {
          onStatusChange(updatedExplorer.id, updatedExplorer.status);
        }

        const status = getExplorerStatus(updatedExplorer.status);
        if (status === "Finished" || status === "Error") {
          clearInterval(intervalId);
        }
      } catch (error) {
        console.error("Failed to fetch explorer status:", error);
        clearInterval(intervalId);
      }
    };

    const currentStatus = getExplorerStatus(explorer.status);
    if (currentStatus !== "Finished" && currentStatus !== "Error") {
      intervalId = setInterval(fetchExplorerStatus, 1500);
    }

    return () => clearInterval(intervalId);
  }, [explorer.id, explorer.status, onStatusChange]);

  const statusLabel = getExplorerStatus(explorer.status);

  return (
    <Card
      key={explorer.id}
      sx={{ bgcolor: "#212121", borderRadius: 2, height: "100%" }}
      className="explorer-box"
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
            <Analytics sx={{ color: "#00BEBB", fontSize: 20 }} />
            <Typography variant="h6">
              {explorerComponent.display_name}
            </Typography>
          </Box>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Chip
              label={statusLabel}
              color={statusLabel === "Finished" ? "primary" : "default"}
              size="small"
            />
            <>
              {statusLabel === "Finished" && (
                <IconButton
                  size="small"
                  onClick={() => handleExplorerDetailsClick(explorer)}
                  sx={{
                    color: "white",
                    width: 24,
                    height: 24,
                    bgcolor: "primary.main",
                    "&:hover": { bgcolor: "primary.dark" },
                  }}
                >
                  <Info sx={{ fontSize: 16 }} />
                </IconButton>
              )}
              {(statusLabel === "Error" || statusLabel === "Finished") && (
                <IconButton
                  size="small"
                  onClick={() => handleExplorerDeleteClick(explorer)}
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
            </>
          </Box>
        </Box>

        {statusLabel === "Finished" ? (
          <Box
            sx={{
              flexGrow: 1,
              bgcolor: "#2e3037",
              borderRadius: 1,
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
            }}
          >
            <TabResults id={explorer.id} minimalist height={300} />
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
            <CircularProgress size={24} sx={{ mr: 1 }} />
            <Typography>Processing...</Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}
