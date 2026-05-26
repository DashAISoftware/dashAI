import React, { useEffect, useState } from "react";
import {
  Box,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  IconButton,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import {
  AddCircleOutline,
  DeleteOutline,
  PlayArrow as PlayArrowIcon,
} from "@mui/icons-material";
import { CircularProgress } from "@mui/material";
import InputField from "./InputField";
import { MIN_INPUT_WIDTH } from "./inputFieldConstants";
import { useTranslation } from "react-i18next";

const HEADER_HEIGHT = 40;
const ROW_HEIGHT = 52;

const cellBase = {
  padding: "6px 12px",
  whiteSpace: "nowrap",
  minWidth: 110,
};

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
  const [rows, setRows] = useState(createInitialRows());
  const { t } = useTranslation(["prediction"]);

  function createInitialRows() {
    if (manualInputData && manualInputData.length > 0) {
      return manualInputData;
    }
    const initialRow = createEmptyRow();
    setManualInputData([initialRow]);
    return [initialRow];
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

  const handleChange = (rowIndex, col, value) => {
    const newRows = [...rows];
    newRows[rowIndex] = { ...newRows[rowIndex], [col]: value };
    setRows(newRows);
    setManualInputData(newRows);
  };

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
      ? "rgba(255, 255, 255, 0.05)"
      : "rgba(0, 0, 0, 0.02)";

  const targetLabel = predictionResults
    ? predictionResults.columns[predictionResults.columns.length - 1]
    : targetColumn;

  return (
    <Box
      sx={{
        borderRadius: 1,
        color: theme.palette.text.primary,
        maxWidth: "100%",
        mx: "auto",
        height: "100%",
      }}
      component="form"
      onSubmit={handleSubmit}
    >
      <Typography variant="h6" mb={2} fontWeight={600}>
        {t("prediction:label.manualInputData")}
      </Typography>
      <Typography
        variant="body2"
        mb={3}
        sx={{ color: theme.palette.text.secondary }}
      >
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
          border: `1px solid ${theme.palette.divider}`,
          borderRadius: 1,
          overflow: "auto",
          boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
        }}
      >
        {/* Scrollable input columns */}
        <Box sx={{ flex: 1, overflowX: "auto" }}>
          <Table
            size="small"
            sx={{
              "& .MuiTableCell-root": {
                borderBottom: `1px solid ${theme.palette.divider}`,
              },
            }}
          >
            <TableHead>
              <TableRow
                sx={{ backgroundColor: headerBg, height: HEADER_HEIGHT }}
              >
                {inputColumns.map((col) => (
                  <TableCell
                    key={col}
                    sx={{
                      ...cellBase,
                      fontWeight: 600,
                      fontSize: "0.875rem",
                      color: theme.palette.text.primary,
                      height: HEADER_HEIGHT,
                    }}
                  >
                    {col}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row, rowIndex) => (
                <TableRow
                  key={rowIndex}
                  sx={{
                    height: ROW_HEIGHT,
                    "&:hover": {
                      backgroundColor:
                        theme.palette.mode === "dark"
                          ? "rgba(255, 255, 255, 0.03)"
                          : "rgba(0, 0, 0, 0.01)",
                    },
                    "&:last-child .MuiTableCell-root": { borderBottom: "none" },
                  }}
                >
                  {inputColumns.map((col) => (
                    <TableCell
                      key={col}
                      sx={{
                        ...cellBase,
                        color: theme.palette.text.primary,
                        height: ROW_HEIGHT,
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
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>

        {/* Fixed: target + delete */}
        <Box
          sx={{
            flexShrink: 0,
            borderLeft: `2px solid ${predictionResults ? theme.palette.primary.main : theme.palette.divider}`,
          }}
        >
          <Table
            size="small"
            sx={{
              "& .MuiTableCell-root": {
                borderBottom: `1px solid ${theme.palette.divider}`,
              },
            }}
          >
            <TableHead>
              <TableRow
                sx={{ backgroundColor: headerBg, height: HEADER_HEIGHT }}
              >
                <TableCell
                  sx={{
                    ...cellBase,
                    fontWeight: 600,
                    fontSize: "0.875rem",
                    color: theme.palette.primary.main,
                    minWidth: 120,
                    height: HEADER_HEIGHT,
                  }}
                >
                  {targetLabel ?? ""}
                </TableCell>
                <TableCell
                  sx={{
                    ...cellBase,
                    fontWeight: 600,
                    fontSize: "0.875rem",
                    color: theme.palette.text.primary,
                    width: 60,
                    textAlign: "center",
                    borderLeft: `1px solid ${theme.palette.divider}`,
                    height: HEADER_HEIGHT,
                  }}
                >
                  {t("common:remove")}
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row, rowIndex) => {
                const predVal = predictionResults
                  ? predictionResults.rows[rowIndex]?.[
                      predictionResults.rows[rowIndex]?.length - 1
                    ]
                  : undefined;
                return (
                  <TableRow
                    key={rowIndex}
                    sx={{
                      height: ROW_HEIGHT,
                      "&:last-child .MuiTableCell-root": {
                        borderBottom: "none",
                      },
                    }}
                  >
                    <TableCell
                      sx={{
                        ...cellBase,
                        fontWeight: 500,
                        fontSize: "0.875rem",
                        color: theme.palette.primary.main,
                        minWidth: 120,
                        height: ROW_HEIGHT,
                      }}
                    >
                      {predVal !== null && predVal !== undefined
                        ? String(predVal)
                        : ""}
                    </TableCell>
                    <TableCell
                      sx={{
                        ...cellBase,
                        textAlign: "center",
                        borderLeft: `1px solid ${theme.palette.divider}`,
                        height: ROW_HEIGHT,
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
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Box>
      </Box>
    </Box>
  );
}
