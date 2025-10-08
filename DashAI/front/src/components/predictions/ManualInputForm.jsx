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
}) {
  const [rows, setRows] = useState([createEmptyRow()]);
  console.log(sample);

  function createEmptyRow() {
    const row = {};
    inputColumns.forEach((col) => (row[col] = sample[col][0]));
    return row;
  }

  useEffect(() => {
    console.log("rows updated:", rows);
  }, [rows]);

  const handleChange = (rowIndex, col, value) => {
    const newRows = [...rows];
    newRows[rowIndex][col] = value;
    setRows(newRows);
  };

  const handleAddRow = () => setRows([...rows, createEmptyRow()]);

  const handleDeleteRow = (index) => {
    const newRows = rows.filter((_, i) => i !== index);
    setRows(newRows);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (onSubmit) onSubmit(rows);
    console.log("Submitted rows:", rows);
  };

  return (
    <Box
      sx={{
        p: 3,
        borderRadius: 2,
        backgroundColor: "#1e1e1e",
        color: "white",
        boxShadow: 3,
        maxWidth: "90%",
        mx: "auto",
      }}
      component="form"
      onSubmit={handleSubmit}
    >
      <Typography variant="h6" mb={2} fontWeight={600}>
        Manual Input
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
