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
import { AddCircleOutline, DeleteOutline } from "@mui/icons-material";
import { renderInputField } from "./renderInputField";

export default function ManualInputForm({
  types,
  sample,
  inputColumns,
  onSubmit,
  manualInputData,
  setManualInputData,
}) {
  const [rows, setRows] = useState(createInitialRows());

  function createInitialRows() {
    if (manualInputData && manualInputData.length > 0) {
      return manualInputData;
    }
    setManualInputData([createEmptyRow()]);
    return [createEmptyRow()];
  }

  function createEmptyRow() {
    const row = {};
    inputColumns.forEach((col) => {
      const typeInfo = types[col];
      if (
        typeInfo?.type === "Categorical" &&
        typeInfo?.categories?.length > 0
      ) {
        row[col] = typeInfo.categories[0];
      } else {
        row[col] = sample[col][0];
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
    console.log("Submitted rows:", rows);
  };

  return (
    <Box
      sx={{
        p: 2,
        borderRadius: 1,
        backgroundColor: "#1e1e1e",
        color: "white",
        boxShadow: 3,
        maxWidth: "100%",
        mx: "auto",
      }}
      component="form"
      onSubmit={handleSubmit}
    >
      <Typography variant="h6" mb={2} fontWeight={600}>
        Manual Input
      </Typography>
      <Typography variant="body2" mb={3} color="text.secondary">
        Enter data manually for prediction. Fill in the fields below and submit
        when ready.
      </Typography>

      <TableContainer component={Paper} sx={{ backgroundColor: "#2a2a2a" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              {inputColumns.map((col) => (
                <TableCell key={col} sx={{ color: "#fff", fontWeight: 600 }}>
                  {col}
                </TableCell>
              ))}
              <TableCell sx={{ color: "#fff", fontWeight: 600 }}>
                Actions
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
          Add row
        </Button>
      </Box>
    </Box>
  );
}
