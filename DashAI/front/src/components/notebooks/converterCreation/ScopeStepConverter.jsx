import { useState, useEffect } from "react";
import { Box, Typography, Tooltip, IconButton } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import ConverterClassColumnModal from "./ConverterTargetColumnModal";
import HelpIcon from "@mui/icons-material/Help";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";
import ColumnSelector from "../ColumnSelector";
import { RowSelector } from "../RowSelector";
import {
  getDatasetInfoByFilePath,
  getDatasetTypesByFilePath,
} from "../../../api/datasets";
import { useTourContext } from "../../tour/TourProvider";

export default function ScopeStepConverter({
  supervised,
  targetColumn,
  setTargetColumn,
  tool,
  rows,
  setRows,
  columns,
  setColumns,
  notebook,
  nextStep,
}) {
  const theme = useTheme();
  const [datasetInfo, setDatasetInfo] = useState(0);
  const [datasetColumns, setDatasetColumns] = useState([]);
  const tourContext = useTourContext();
  const allowedDtypes = tool?.metadata?.allowed_dtypes || [];
  const restrictedDtypes = tool?.metadata?.restricted_dtypes || [];

  const handleSubmit = () => {
    nextStep();
    if (tourContext && tourContext.run) {
      setTimeout(() => {
        tourContext.nextStep();
      }, 500);
    }
  };
  const [isColumnSelectionValid, setIsColumnSelectionValid] = useState(false);

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
      data-tour="column-selector-converter-container"
    >
      {/* Content */}
      <Box
        sx={{
          flexGrow: 1,
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: 1,
        }}
      >
        <Typography variant="subtitle2" gutterBottom>
          Step 1: Select Scope
        </Typography>
        <Typography
          variant="body2"
          sx={{ color: theme.palette.text.secondary }}
        >
          Here you will configure which columns to apply the converter to.
        </Typography>
        {/* Scope selection UI */}
        <ColumnSelector
          file_path={notebook.file_path}
          allowedDtypes={allowedDtypes}
          restrictedDtypes={restrictedDtypes}
          onSelectionChange={(columnsInfo) => {
            const processedColumns = columnsInfo.map((col) => ({
              idx: col.id + 1,
              columnName: col.columnName,
              valueType: col.valueType,
              dataType: col.dataType,
            }));
            setColumns(processedColumns);
          }}
          onValidationChange={(isValid) => setIsColumnSelectionValid(isValid)}
        />
        <Typography
          variant="body2"
          sx={{ color: theme.palette.text.secondary }}
        >
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
          mb: 4,
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
            updateClassColumn={(column) => {
              const processedColumn = {
                idx: column.id + 1,
                columnName: column.columnName,
                valueType: column.valueType,
                dataType: column.dataType,
              };
              setTargetColumn(processedColumn);
            }}
            classColumnInitialValue={targetColumn?.idx}
            notebook={notebook}
          />
        )}

        <FormSchemaButtonGroup
          onFormSubmit={handleSubmit}
          error={
            !isColumnSelectionValid || (supervised ? !targetColumn : false)
          }
          saveButtonText={
            Object.values(tool.schema.properties).length > 0 ? "Next" : "Save"
          }
          data-tour="converter-scope-next-button"
        />
      </Box>
    </Box>
  );
}
