import React, { useState } from "react";
import { Box, Button, Typography } from "@mui/material";
import ConfigureToolModal from "./toolModal/ConfigureToolModal";
import FormConverterSection from "./converterModals/FormConverterSection";

export default function ConverterList({
  converters,
  hoveredTool,
  setHoveredTool,
  notebook,
}) {
  const handleConverterClick = (converter) => {
    setSelectedConverter(converter);
    setOpen(true);
  };

  const [open, setOpen] = useState(false);
  const [selectedConverter, setSelectedConverter] = useState(null);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
      {converters.length === 0 ? (
        <Typography
          variant="body2"
          sx={{
            color: "text.secondary",
            textAlign: "center",
            py: 2,
          }}
        >
          No converters found matching your search.
        </Typography>
      ) : (
        converters.map((converter) => (
          <Button
            key={converter.name}
            variant="contained"
            sx={{
              bgcolor: hoveredTool === converter.type ? "#444" : "#333",
              color: "white",
              justifyContent: "flex-start",
              textTransform: "none",
              fontWeight: "normal",
              py: 1.5,
              "&:hover": { bgcolor: "#444" },
            }}
            onMouseEnter={() => setHoveredTool(converter)}
            onMouseLeave={() => setHoveredTool(null)}
            onClick={() => handleConverterClick(converter)}
          >
            {converter.name}
          </Button>
        ))
      )}
      {selectedConverter && (
        <ConfigureToolModal
          open={open}
          handleClose={() => {
            setOpen(false);
            setSelectedConverter(null);
          }}
          tool={selectedConverter}
          notebook={notebook}
          FormSection={FormConverterSection}
        />
      )}
    </Box>
  );
}
