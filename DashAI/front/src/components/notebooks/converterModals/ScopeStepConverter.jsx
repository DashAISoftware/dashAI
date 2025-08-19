import React from "react";
import { Box, Typography, Tooltip, IconButton, Button } from "@mui/material";
import ConverterClassColumnModal from "./ConverterClassColumnModal";
import HelpIcon from "@mui/icons-material/Help";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";
import ColumnSelectionTable from "../../threeSectionLayout/ColumnSelectionTable";
import { RowSelector } from "../RowSelector";

export default function ScopeStepConverter({
  targetColumn,
  setTargetColumn,
  rows,
  setRows,
  columns,
  setColumns,
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
      <Box
        sx={{
          flexGrow: 1,
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: 2,
        }}
      >
        <Typography variant="subtitle2" gutterBottom>
          Step 1: Select Scope
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Here you will configure which columns to apply the converter to.
        </Typography>
        {/* Scope selection UI */}
        <ColumnSelectionTable
          datasetColumns={[]}
          onSelectionChange={() => {}}
          onValidationChange={() => {}}
          description=""
        />
        <Typography variant="body2" color="text.secondary">
          Here you will configure which rows to apply the converter to.
        </Typography>
        <RowSelector
          totalRows={100}
          initialRows={rows}
          onSelectionChange={(selectedRows) => {
            console.log("Selected rows:", selectedRows);
            setRows(selectedRows);
          }}
        />
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
          updateClassColumn={setTargetColumn}
          classColumnInitialValue={targetColumn}
          notebook={notebook}
        />
        <FormSchemaButtonGroup
          onFormSubmit={() => setStep((s) => s + 1)}
          error={!targetColumn}
          saveButtonText="Next"
        />
      </Box>
    </Box>
  );
}
