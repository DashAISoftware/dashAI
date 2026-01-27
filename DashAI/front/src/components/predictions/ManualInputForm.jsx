import React, { useEffect, useState } from "react";
import {
  Box,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { AddCircleOutline, DeleteOutline } from "@mui/icons-material";
import { renderInputField } from "./renderInputField";
import { useTranslation } from "react-i18next";

export default function ManualInputForm({
  types,
  sample,
  inputColumns,
  onSubmit,
  manualInputData,
  setManualInputData,
}) {
  const theme = useTheme();
  const [rows, setRows] = useState(createInitialRows());
  const { t } = useTranslation(["prediction"]);

  function createInitialRows() {
    if (manualInputData && manualInputData.length > 0) {
      return manualInputData;
    }
    setManualInputData([createEmptyRow()]);
    return [createEmptyRow()];
  }

  function createEmptyRow() {
    const row = {};
    const randomIndex = Math.floor(
      Math.random() * sample[inputColumns[0]].length,
    );
    inputColumns.forEach((col) => {
      const typeInfo = types[col];
      if (
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
    newRows[rowIndex][col] = value;
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

  return (
    <Box
      sx={{
        borderRadius: 1,
        color: "white",
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

      <TableContainer component={Paper} sx={{ p: 1 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              {inputColumns.map((col) => (
                <TableCell key={col} sx={{ color: "#fff", fontWeight: 600 }}>
                  {col}
                </TableCell>
              ))}
              <TableCell sx={{ color: "#fff", fontWeight: 600 }}>
                {t("common:remove")}
              </TableCell>
            </TableRow>
          </TableHead>

          <TableBody>
            {rows.map((row, rowIndex) => (
              <TableRow key={rowIndex}>
                {inputColumns.map((col) => (
                  <TableCell key={col} sx={{ color: "#fff" }}>
                    {renderInputField(
                      handleChange,
                      rowIndex,
                      col,
                      types[col],
                      row[col],
                      sample[col][0],
                    )}
                  </TableCell>
                ))}
                <TableCell>
                  <IconButton
                    color="error"
                    onClick={() => handleDeleteRow(rowIndex)}
                    disabled={rows.length === 1}
                  >
                    <DeleteOutline />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 2 }}>
        <Button
          startIcon={<AddCircleOutline />}
          variant="contained"
          color="primary"
          onClick={handleAddRow}
        >
          {t("common:addRow")}
        </Button>
      </Box>
    </Box>
  );
}
