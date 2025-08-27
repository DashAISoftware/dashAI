import { useState, useEffect } from "react";
import { Box, Typography, Tooltip, IconButton } from "@mui/material";
import ConverterClassColumnModal from "./ConverterTargetColumnModal";
import HelpIcon from "@mui/icons-material/Help";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";
import ColumnSelector from "../ColumnSelector";
import { RowSelector } from "../RowSelector";
import {
  getDatasetInfoByFilePath,
  getDatasetTypesByFilePath,
} from "../../../api/datasets";

export default function ScopeStepConverter({
  supervised,
  targetColumn,
  setTargetColumn,
  rows,
  setRows,
  columns,
  setColumns,
  notebook,
  setStep,
}) {
  const [datasetInfo, setDatasetInfo] = useState(0);
  const [datasetColumns, setDatasetColumns] = useState([]);

  useEffect(() => {
    let isMounted = true;

    const fetchAllData = async () => {
      try {
        const [data, types] = await Promise.all([
          getDatasetInfoByFilePath(notebook.file_path),
          getDatasetTypesByFilePath(notebook.file_path),
        ]);

        if (!isMounted) return;

        setDatasetInfo(data);

        const datasetColumns = Object.entries(types).map(
          ([columnName, typeInfo], idx) => ({
            id: idx,
            columnName: columnName,
            valueType: typeInfo.type || "Unknown",
            dataType: typeInfo.dtype || "Unknown",
            order: idx,
          }),
        );

        setDatasetColumns(datasetColumns);
      } catch (error) {
        console.error("Error fetching dataset info/types:", error);
      }
    };

    fetchAllData();

    return () => {
      isMounted = false;
    };
  }, [notebook.file_path]);

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
        <ColumnSelector
          file_path={notebook.file_path}
          onSelectionChange={(columnsInfo) => {
            const selectedOrders = columnsInfo.map((col) => col.id + 1);
            setColumns(selectedOrders);
          }}
          onValidationChange={() => {}}
        />
        <Typography variant="body2" color="text.secondary">
          Here you will configure which rows to apply the converter to.
        </Typography>
        <RowSelector
          totalRows={datasetInfo?.total_rows || 0}
          initialRows={rows}
          onSelectionChange={(selectedRows) => {
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
        {supervised && (
          <Tooltip
            title="Supervised converters will include this column in their learning process."
            placement="top"
          >
            <IconButton>
              <HelpIcon />
            </IconButton>
          </Tooltip>
        )}

        {supervised && (
          <ConverterClassColumnModal
            updateClassColumn={setTargetColumn}
            classColumnInitialValue={targetColumn}
            notebook={notebook}
          />
        )}

        <FormSchemaButtonGroup
          onFormSubmit={() => setStep((s) => s + 1)}
          error={supervised ? !targetColumn : false}
          saveButtonText="Next"
        />
      </Box>
    </Box>
  );
}
