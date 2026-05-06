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
import { useTranslation } from "react-i18next";

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
  hideButtons = false,
}) {
  const theme = useTheme();
  const [datasetInfo, setDatasetInfo] = useState(0);
  const [datasetColumns, setDatasetColumns] = useState([]);
  const tourContext = useTourContext();
  const allowedTypes = tool?.metadata?.allowed_types || [];
  const allowedDtypes = tool?.metadata?.allowed_dtypes || [];
  const { t } = useTranslation(["common", "datasets"]);

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
            valueType: typeInfo.type || t("common:unknown"),
            dataType: typeInfo.dtype || t("common:unknown"),
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
        flex: 1,
        height: "100%",
        minHeight: 0,
      }}
      data-tour="column-selector-converter-container"
    >
      {/* Content */}
      <Box
        sx={{
          flex: 1,
          minHeight: 0,
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: 1,
        }}
      >
        <Typography
          variant="h6"
          sx={{ fontWeight: 700, color: theme.palette.primary.main, mb: 0.5 }}
        >
          {t("datasets:label.selectScopeStep", { step: 1 })}
        </Typography>
        <Typography
          variant="body2"
          sx={{ color: theme.palette.text.primary, mb: 0.5 }}
        >
          {t("datasets:label.selectScopeDescriptionColumns")}
        </Typography>
        {/* Scope selection UI */}
        <ColumnSelector
          file_path={notebook.file_path}
          allowedTypes={allowedTypes}
          allowedDtypes={allowedDtypes}
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
          {t("datasets:label.selectScopeDescriptionRows")}
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
          justifyContent: "flex-end",
          gap: 1,
          pt: 1,
        }}
      >
        {supervised && (
          <Tooltip
            title={t("datasets:label.helpSelectClassColumn")}
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
      </Box>

      {/* Buttons */}
      <FormSchemaButtonGroup
        onFormSubmit={handleSubmit}
        error={!isColumnSelectionValid || (supervised ? !targetColumn : false)}
        saveButtonText={
          Object.values(tool.schema.properties).length > 0
            ? t("common:next")
            : t("common:save")
        }
        data-tour="converter-scope-next-button"
      />
    </Box>
  );
}
