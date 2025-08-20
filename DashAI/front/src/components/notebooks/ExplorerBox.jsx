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
import { Analytics, Info } from "@mui/icons-material";
import Results from "./ExplorerDetailTabs/Results";
import { getExplorerStatus } from "../../utils/explorerStatus";
import { getExplorerById } from "../../api/explorer";

export default function ExplorerBox({ explorer, handleExplorerDetailsClick }) {
  const [explorerState, setExplorerState] = useState(explorer);

  useEffect(() => {
    let intervalId;

    const fetchExplorerStatus = async () => {
      try {
        const updatedExplorer = await getExplorerById(explorer.id);
        setExplorerState(updatedExplorer);

        const status = getExplorerStatus(updatedExplorer.status);
        if (status === "Finished" || status === "Error") {
          clearInterval(intervalId); // stop polling
        }
      } catch (error) {
        console.error("Failed to fetch explorer status:", error);
        clearInterval(intervalId); // stop polling on error
      }
    };

    const currentStatus = getExplorerStatus(explorerState.status);
    if (currentStatus !== "Finished" && currentStatus !== "Error") {
      intervalId = setInterval(fetchExplorerStatus, 1500); // polling every 1.5s
    }

    return () => clearInterval(intervalId);
  }, [explorer.id, explorerState.status]);

  const statusLabel = getExplorerStatus(explorerState.status);

  return (
    <Card key={explorer.id} sx={{ bgcolor: "#212121", borderRadius: 2 }}>
      <CardContent>
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
              {explorerState.exploration_type}
            </Typography>
          </Box>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Chip
              label={statusLabel}
              color={statusLabel === "Finished" ? "primary" : "default"}
              size="small"
            />
            {statusLabel === "Finished" && (
              <IconButton
                size="small"
                onClick={() => handleExplorerDetailsClick(explorerState)}
                sx={{
                  bgcolor: "#00BEBB",
                  color: "white",
                  width: 24,
                  height: 24,
                  "&:hover": { bgcolor: "#008582" },
                }}
              >
                <Info sx={{ fontSize: 16 }} />
              </IconButton>
            )}
          </Box>
        </Box>

        {statusLabel === "Finished" ? (
          <Box
            sx={{
              bgcolor: "#2e3037",
              borderRadius: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Results id={explorerState.id} minimalist height={300} />
          </Box>
        ) : statusLabel === "Error" ? (
          <Box
            sx={{
              height: 120,
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
              height: 120,
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
