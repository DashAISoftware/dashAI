import React, { useState } from "react";
import { Box, Button, Typography } from "@mui/material";
import ConfigureToolModal from "../ConfigureToolModal";
import FormConverterSection from "./FormConverterSection";
import { useTourContext } from "../../tour/TourProvider";

export default function ConverterList({
  converters,
  hoveredTool,
  setHoveredTool,
  notebook,
}) {
  const [open, setOpen] = useState(false);
  const [selectedConverter, setSelectedConverter] = useState(null);
  const tourContext = useTourContext();

  const handleConverterClick = (converter) => {
    setSelectedConverter(converter);
    setOpen(true);

    if (tourContext && tourContext.run) {
      if (converter.name === "LabelEncoder" || converter.name === "NanRemover") {
        setTimeout(() => {
          tourContext.nextStep();
        }, 500);
      }
    }
  };


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
        converters.map((converter) => {
          const getTourAttribute = () => {
            if (converter.name === "LabelEncoder") {
              return "label-encoder-converter";
            }
            if (converter.name === "NanRemover") {
              return "nan-remover-converter";
            }
            return null;
          };

          const tourAttr = getTourAttribute();

          return (
            <Button
              key={converter.name}
              variant="contained"
              data-tour={tourAttr || undefined}
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
              {converter.display_name}
            </Button>
          );
        })
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