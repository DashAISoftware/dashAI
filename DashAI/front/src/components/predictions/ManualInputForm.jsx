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
import InputField from "./InputField";
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
        color: theme.palette.text.primary,
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
      <Typography
        variant="body2"
        mb={6}
        sx={{ color: theme.palette.text.secondary }}
      >
        {t("prediction:label.provideManualInput")}
      </Typography>

      <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 2 }}>
        <Button
          startIcon={<AddCircleOutline />}
          variant="outlined"
          onClick={handleAddRow}
          sx={{
            textTransform: "none",
            fontWeight: 500,
          }}
        >
          {t("common:addRow")}
        </Button>
      </Box>

      <TableContainer
        component={Paper}
        sx={{
          border: `1px solid ${theme.palette.divider}`,
          borderRadius: 1,
          overflow: "hidden",
          boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
        }}
      >
        <Table
          size="small"
          sx={{
            "& .MuiTableCell-root": {
              borderBottom: `1px solid ${theme.palette.divider}`,
              padding: "8px 12px",
            },
          }}
        >
          <TableHead>
            <TableRow
              sx={{
                backgroundColor:
                  theme.palette.mode === "dark"
                    ? "rgba(255, 255, 255, 0.05)"
                    : "rgba(0, 0, 0, 0.02)",
              }}
            >
              {inputColumns.map((col) => (
                <TableCell
                  key={col}
                  sx={{
                    fontWeight: 600,
                    fontSize: "0.875rem",
                    color: theme.palette.text.primary,
                    textTransform: "none",
                    whiteSpace: "nowrap",
                  }}
                >
                  {col}
                </TableCell>
              ))}
              <TableCell
                sx={{
                  fontWeight: 600,
                  fontSize: "0.875rem",
                  color: theme.palette.text.primary,
                  width: "60px",
                  textAlign: "center",
                }}
              >
                {t("common:remove")}
              </TableCell>
            </TableRow>
          </TableHead>

          <TableBody>
            {rows.map((row, rowIndex) => (
              <TableRow
                key={rowIndex}
                sx={{
                  "&:hover": {
                    backgroundColor:
                      theme.palette.mode === "dark"
                        ? "rgba(255, 255, 255, 0.03)"
                        : "rgba(0, 0, 0, 0.01)",
                  },
                  "&:last-child .MuiTableCell-root": {
                    borderBottom: "none",
                  },
                }}
              >
                {inputColumns.map((col) => (
                  <TableCell
                    key={col}
                    sx={{
                      color: theme.palette.text.primary,
                      padding: "6px 12px",
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
                <TableCell sx={{ padding: "6px 12px", textAlign: "center" }}>
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
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
