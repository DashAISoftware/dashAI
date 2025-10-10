import React, { useState } from "react";
import { Box, Button, Typography } from "@mui/material";
import ConfigureToolModal from "../ConfigureToolModal";
import FormConverterSection from "./FormConverterSection";
import ToolListItem from "../explorerCreation/ToolListItem";

export default function ConverterList({ converters, notebook }) {
  const handleConverterClick = (converter) => {
    setSelectedConverter(converter);
    setOpen(true);
  };

  const [open, setOpen] = useState(false);
  const [selectedConverter, setSelectedConverter] = useState(null);

  return (
    <Box sx={{ display: "flex", flexDirection: "column" }}>
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
          <ToolListItem
            key={converter.name}
            tool={converter}
            onClick={() => handleConverterClick(converter)}
          />
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
