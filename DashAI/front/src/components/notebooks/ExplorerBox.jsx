import React from "react";
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
import Results from "./Results";
import { getExplorerStatus } from "../../utils/explorerStatus";

export default function ExplorerBox({ explorer, handleExplorerDetailsClick }) {
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
            <Typography variant="h6">{explorer.name}</Typography>
          </Box>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Chip
              label={getExplorerStatus(explorer.status)}
              color={
                getExplorerStatus(explorer.status) === "Finished"
                  ? "primary"
                  : "default"
              }
              size="small"
            />
            {getExplorerStatus(explorer.status) === "Finished" && (
              <IconButton
                size="small"
                onClick={() => handleExplorerDetailsClick(explorer)}
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
        {getExplorerStatus(explorer.status) === "Finished" ? (
          <Box
            sx={{
              bgcolor: "#2e3037",
              borderRadius: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Results id={explorer.id} />
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
