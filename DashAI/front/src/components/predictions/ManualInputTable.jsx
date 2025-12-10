import React from "react";
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  TextField,
  IconButton,
  Button,
  Chip,
} from "@mui/material";
import { Delete as DeleteIcon, Add as AddIcon } from "@mui/icons-material";

const mockInputColumns = ["CO(GT)", "PT08.S1(CO)", "C6H6(GT)", "T", "RH"];

function ManualInputTable({ manualRows, setManualRows }) {
  const handleAddRow = () => {
    setManualRows([...manualRows, { id: Date.now().toString(), values: {} }]);
  };

  const handleRemoveRow = (rowId) => {
    if (manualRows.length > 1) {
      setManualRows(manualRows.filter((r) => r.id !== rowId));
    }
  };

  const handleCellChange = (rowId, column, value) => {
    setManualRows(
      manualRows.map((row) =>
        row.id === rowId
          ? { ...row, values: { ...row.values, [column]: value } }
          : row,
      ),
    );
  };

  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600 }}>
        Input Columns
      </Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mb: 2 }}>
        {mockInputColumns.map((column) => (
          <Chip key={column} label={column} size="small" />
        ))}
      </Box>

      <TableContainer component={Paper} sx={{ maxHeight: 400 }}>
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow>
              <TableCell>#</TableCell>
              {mockInputColumns.map((column) => (
                <TableCell key={column}>{column}</TableCell>
              ))}
              <TableCell width={50}></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {manualRows.map((row, index) => (
              <TableRow key={row.id}>
                <TableCell>{index + 1}</TableCell>
                {mockInputColumns.map((column) => (
                  <TableCell key={column}>
                    <TextField
                      size="small"
                      value={row.values[column] || ""}
                      onChange={(e) =>
                        handleCellChange(row.id, column, e.target.value)
                      }
                      placeholder="-"
                      fullWidth
                    />
                  </TableCell>
                ))}
                <TableCell>
                  <IconButton
                    size="small"
                    onClick={() => handleRemoveRow(row.id)}
                    disabled={manualRows.length === 1}
                    color="error"
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Button
        fullWidth
        startIcon={<AddIcon />}
        onClick={handleAddRow}
        sx={{ mt: 1 }}
        variant="outlined"
      >
        Add Row
      </Button>
    </Box>
  );
}

export default ManualInputTable;
