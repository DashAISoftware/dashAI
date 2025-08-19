import React from "react";
import { Box, Typography, Tooltip, IconButton, Button } from "@mui/material";
import ConverterClassColumnModal from "./ConverterClassColumnModal";
import HelpIcon from "@mui/icons-material/Help";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";

export default function ScopeStepConverter({
  classColumnInitialValue,
  setClassColumnInitialValue,
  notebook,
  setStep,
}) {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        flexGrow: 1,
        height: "100%",
        gap: 1,
      }}
    >
      {/* Content */}
      <Box sx={{ flexGrow: 1, overflowY: "auto" }}>
        <Typography variant="subtitle2" gutterBottom>
          Step 1: Select Scope
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Here you will configure which columns/rows to apply the converter to.
        </Typography>
        {/* placeholder: scope selection UI */}
      </Box>

      {/* Buttons */}
      <Box
        sx={{
          flexShrink: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "flex-end",
          gap: 1,
        }}
      >
        <Tooltip
          title="Supervised converters will include this column in their learning process."
          placement="top"
        >
          <IconButton>
            <HelpIcon />
          </IconButton>
        </Tooltip>
        <ConverterClassColumnModal
          updateClassColumn={setClassColumnInitialValue}
          classColumnInitialValue={classColumnInitialValue}
          notebook={notebook}
        />
        <FormSchemaButtonGroup
          onFormSubmit={() => setStep((s) => s + 1)}
          error={!classColumnInitialValue}
          saveButtonText="Next"
        />
      </Box>
    </Box>
  );
}
