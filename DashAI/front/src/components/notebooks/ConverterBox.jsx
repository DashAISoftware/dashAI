import React, { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  Box,
  Typography,
  Chip,
  CircularProgress,
} from "@mui/material";
import Transform from "@mui/icons-material/Transform";
import { getConverterStatus } from "../../utils/converterStatus";
import { getComponentById } from "../../api/component";

export default function ConverterBox({ converter }) {
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
  }, []);

  return (
    <Card key={converter.id} sx={{ bgcolor: "#212121", borderRadius: 2 }}>
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
            <Transform sx={{ color: "#00BEBB", fontSize: 20 }} />
            <Typography variant="h6">{converter.converter}</Typography>
          </Box>
          <Chip
            label={getConverterStatus(converter.status)}
            color={
              getConverterStatus(converter.status) === "Finished"
                ? "primary"
                : "default"
            }
            size="small"
          />
        </Box>
        {getConverterStatus(converter.status) === "Finished" ? (
          <Box
            sx={{
              height: 80,
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
              sx={{ color: "text.secondary", textAlign: "center" }}
            >
              {converterComponent.description}
            </Typography>
          </Box>
        ) : (
          <Box
            sx={{
              height: 80,
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
