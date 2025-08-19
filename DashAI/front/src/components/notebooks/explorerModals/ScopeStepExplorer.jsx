import React, { useEffect, useState } from "react";
import { Box, Typography } from "@mui/material";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";
import ColumnSelectionTable from "../../threeSectionLayout/ColumnSelectionTable";
import { getDatasetFile } from "../../../api/datasets";

export default function ScopeStepExplorer({
  notebook,
  tool,
  setScopeColumns,
  setStep,
}) {
  const [datasetColumns, setDatasetColumns] = useState([]);
  const [isSelectionValid, setIsSelectionValid] = useState(false);

  useEffect(() => {
    const fetchDatasetData = async () => {
      if (notebook?.file_path) {
        try {
          const datasetFile = await getDatasetFile(notebook.file_path, 0, 1);
          if (datasetFile.rows && datasetFile.rows.length > 0) {
            const firstRow = datasetFile.rows[0];
            const columnNames = Object.keys(firstRow);
            const cols = columnNames.map((columnName, index) => {
              const value = firstRow[columnName];
              let dataType = "unknown";
              let valueType = "unknown";
              if (typeof value === "number") {
                dataType = Number.isInteger(value) ? "int64" : "float64";
                valueType = "Value";
              } else if (typeof value === "string") {
                dataType = "object";
                valueType = "Category";
              } else if (typeof value === "boolean") {
                dataType = "bool";
                valueType = "Category";
              }
              return {
                id: index,
                columnName: columnName,
                valueType: valueType,
                dataType: dataType,
              };
            });
            setDatasetColumns(cols);
          }
        } catch (error) {
          console.error("Error fetching notebook dataset data:", error);
        }
      }
    };
    fetchDatasetData();
  }, [notebook?.file_path]);

  const allowedDtypes = tool?.metadata?.allowed_dtypes || [];
  const restrictedDtypes = tool?.metadata?.restricted_dtypes || [];
  const inputCardinality = tool?.metadata?.input_cardinality || {};

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
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          Select the columns to be used by the explorer.
        </Typography>

        <ColumnSelectionTable
          datasetColumns={datasetColumns}
          inputCardinality={inputCardinality}
          allowedDtypes={allowedDtypes}
          restrictedDtypes={restrictedDtypes}
          onSelectionChange={(selected) => setScopeColumns(selected)}
          onValidationChange={setIsSelectionValid}
          title={`Select the columns you want to use for ${tool?.name}`}
          description=""
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
        <FormSchemaButtonGroup
          onFormSubmit={() => setStep((s) => s + 1)}
          error={!isSelectionValid}
          saveButtonText="Next"
        />
      </Box>
    </Box>
  );
}
