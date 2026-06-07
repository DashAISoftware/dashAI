import React, { useCallback, useState } from "react";
import { Box, Button, IconButton, Typography } from "@mui/material";
import { CircularProgress } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import {
  AddCircleOutline,
  DeleteOutline,
  PlayArrow as PlayArrowIcon,
} from "@mui/icons-material";
import { useTranslation } from "react-i18next";

import InputField from "./InputField";

const HEADER_HEIGHT = 40;
const ROW_HEIGHT = 52;

export default function ManualInputForm({
  types,
  sample,
  inputColumns,
  onSubmit,
  manualInputData,
  setManualInputData,
  predictionResults = null,
  targetColumn = null,
  onRun = null,
  isPreviewing = false,
  isSaving = false,
}) {
  const theme = useTheme();
  const [rows, setRows] = useState(createInitialRows);
  const { t } = useTranslation(["prediction", "common"]);

  function createInitialRows() {
    if (manualInputData && manualInputData.length > 0) return manualInputData;
    const initial = createEmptyRow();
    setManualInputData([initial]);
    return [initial];
  }

  function createEmptyRow() {
    const row = {};
    const randomIndex = Math.floor(
      Math.random() * sample[inputColumns[0]].length,
    );
    inputColumns.forEach((col) => {
      const typeInfo = types[col];
      if (typeInfo?.type === "Image") {
        row[col] = null;
      } else if (
        typeInfo?.type === "Categorical" &&
        typeInfo?.categories?.length > 0
      ) {
        row[col] =
          typeInfo.categories[randomIndex % typeInfo.categories.length];
      } else {
        row[col] = sample[col][randomIndex];
      }
    });
    return row;
  }

  const handleChange = useCallback(
    (rowIndex, col, value) => {
      setRows((prev) => {
        const newRows = [...prev];
        newRows[rowIndex] = { ...newRows[rowIndex], [col]: value };
        setManualInputData(newRows);
        return newRows;
      });
    },
    [setManualInputData],
  );

  const handleAddRow = () => {
    const newRows = [...rows, createEmptyRow()];
    setRows(newRows);
    setManualInputData(newRows);
  };

  const handleDeleteRow = (index) => {
    const newRows = rows.filter((_, i) => i !== index);
    setRows(newRows);
    setManualInputData(newRows);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (onSubmit) onSubmit(rows);
  };

  const headerBg =
    theme.palette.mode === "dark"
      ? "rgba(255,255,255,0.05)"
      : "rgba(0,0,0,0.02)";

  const divider = theme.palette.divider;
  const textPrimary = theme.palette.text.primary;
  const textSecondary = theme.palette.text.secondary;

  const targetLabel = predictionResults
    ? predictionResults.columns[predictionResults.columns.length - 1]
    : targetColumn;

  // Shared plain-<td> styles - no Emotion per-cell cost.
  const thStyle = {
    padding: "8px 12px",
    whiteSpace: "nowrap",
    minWidth: 120,
    fontWeight: 600,
    fontSize: "0.875rem",
    color: textPrimary,
    height: HEADER_HEIGHT,
    background: headerBg,
    borderBottom: `2px solid ${divider}`,
    verticalAlign: "middle",
    textAlign: "left",
  };

  const tdStyle = {
    padding: "6px 12px",
    whiteSpace: "nowrap",
    minWidth: 120,
    color: textPrimary,
    height: ROW_HEIGHT,
    borderBottom: `1px solid ${divider}`,
    verticalAlign: "middle",
  };

  return (
    <Box
      sx={{
        borderRadius: 1,
        color: textPrimary,
        maxWidth: "100%",
        mx: "auto",
        height: "100%",
      }}
      component="form"
      onSubmit={handleSubmit}
    >
      <Typography variant="h6" mb={4} fontWeight={600}>
        {t("prediction:label.manualInputData")}
      </Typography>
      <Typography variant="body2" mb={6} sx={{ color: textSecondary }}>
        {t("prediction:label.provideManualInput")}
      </Typography>

      <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 1, mb: 2 }}>
        <Button
          startIcon={<AddCircleOutline />}
          variant="outlined"
          size="small"
          onClick={handleAddRow}
          sx={{ textTransform: "none", fontWeight: 500 }}
        >
          {t("common:addRow")}
        </Button>
        {onRun && (
          <Button
            variant="contained"
            size="small"
            startIcon={
              isPreviewing ? (
                <CircularProgress size={14} color="inherit" />
              ) : (
                <PlayArrowIcon />
              )
            }
            onClick={onRun}
            disabled={isPreviewing || isSaving || rows.length === 0}
            sx={{ textTransform: "none", fontWeight: 500 }}
          >
            {t("prediction:button.runPrediction")}
          </Button>
        )}
      </Box>

      <Box
        sx={{
          display: "flex",
          border: `1px solid ${divider}`,
          borderRadius: 1,
          overflow: "auto",
          boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
        }}
      >
        {/* Scrollable input columns */}
        <Box sx={{ flex: 1, overflowX: "auto" }}>
          <table
            style={{
              borderCollapse: "collapse",
              tableLayout: "auto",
              width: "max-content",
              minWidth: "100%",
            }}
          >
            <thead>
              <tr>
                {inputColumns.map((col) => (
                  <th key={col} style={thStyle}>
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {inputColumns.map((col) => (
                    <td
                      key={col}
                      style={{
                        ...tdStyle,
                        borderBottom:
                          rowIndex === rows.length - 1
                            ? "none"
                            : `1px solid ${divider}`,
                      }}
                    >
                      <InputField
                        handleChange={handleChange}
                        rowIndex={rowIndex}
                        col={col}
                        typeInfo={types[col]}
                        value={row[col]}
                        placeholder={sample[col][0]}
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </Box>

        {/* Fixed: target + delete */}
        <Box
          sx={{
            flexShrink: 0,
            borderLeft: `2px solid ${predictionResults ? theme.palette.primary.main : divider}`,
          }}
        >
          <table style={{ borderCollapse: "collapse", tableLayout: "auto" }}>
            <thead>
              <tr>
                <th
                  style={{
                    ...thStyle,
                    color: theme.palette.primary.main,
                    minWidth: 120,
                    textAlign: "left",
                  }}
                >
                  {targetLabel ?? ""}
                </th>
                <th
                  style={{
                    ...thStyle,
                    width: 60,
                    textAlign: "center",
                    borderLeft: `1px solid ${divider}`,
                  }}
                >
                  {t("common:remove")}
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, rowIndex) => {
                const predVal = predictionResults
                  ? predictionResults.rows[rowIndex]?.[
                      predictionResults.rows[rowIndex]?.length - 1
                    ]
                  : undefined;
                return (
                  <tr key={rowIndex}>
                    <td
                      style={{
                        ...tdStyle,
                        fontWeight: 500,
                        color: theme.palette.primary.main,
                        minWidth: 120,
                        borderBottom:
                          rowIndex === rows.length - 1
                            ? "none"
                            : `1px solid ${divider}`,
                      }}
                    >
                      {predVal != null ? String(predVal) : ""}
                    </td>
                    <td
                      style={{
                        ...tdStyle,
                        textAlign: "center",
                        borderLeft: `1px solid ${divider}`,
                        borderBottom:
                          rowIndex === rows.length - 1
                            ? "none"
                            : `1px solid ${divider}`,
                      }}
                    >
                      <IconButton
                        size="small"
                        sx={{
                          color: theme.palette.error.main,
                          "&:hover": {
                            backgroundColor: theme.palette.error.light + "20",
                          },
                        }}
                        onClick={() => handleDeleteRow(rowIndex)}
                        disabled={rows.length === 1}
                      >
                        <DeleteOutline fontSize="small" />
                      </IconButton>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Box>
      </Box>
    </Box>
  );
}
