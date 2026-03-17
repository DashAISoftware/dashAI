import React, { useState, useEffect } from "react";
import { DataGrid, GridToolbar } from "@mui/x-data-grid";
import { parseRangeToIndex } from "../../../utils/parseRange";
import PropTypes from "prop-types";
import {
  Box,
  IconButton,
  Typography,
  Button,
  ButtonGroup,
  Dialog,
  DialogContent,
  DialogTitle,
  Stack,
  Tooltip,
  RadioGroup,
  FormControlLabel,
  Radio,
} from "@mui/material";
import { ArrowBackOutlined, ViewColumn } from "@mui/icons-material";
import { parseIndexToRange } from "../../../utils/parseRange";
import TooltipedCellItem from "../../shared/TooltipedCellItem";
import InputWithDebounce from "../../shared/InputWithDebounce";

const columns = [
  {
    field: "columnName",
    headerName: "Column Name",
    flex: 1,
  },
  {
    field: "valueType",
    headerName: "Value Type",
    flex: 0.5,
  },
  {
    field: "dataType",
    headerName: "Data Type",
    flex: 0.5,
  },
];

/**
 * Modal to define the scope of a converter
 * @param {Object} props
 * @param {string} props.elementToConfigure - Name of the converter or chain to configure
 * @param {Function} props.updateScope - Function to update the scope of the element
 * @param {Object} props.scopeInitialValues - Initial values of the scope
 * @param {Object} props.datasetInfo - Information about the dataset
 * @param {number} props.datasetInfo.total_columns - Total number of columns in the dataset
 * @param {number} props.datasetInfo.total_rows - Total number of rows in the dataset
 * @param {Array} props.datasetColumns - Array of dataset columns
 */
const ConverterScopeModal = ({
  elementToConfigure = "",
  updateScope,
  scopeInitialValues,
  datasetInfo = {
    total_columns: 0,
    total_rows: 0,
  },
  datasetColumns,
}) => {
  const [open, setOpen] = useState(false);
  const [inputError, setInputError] = useState({
    columns: "",
    rows: "",
  });
  const [selectedRadioButtons, setSelectedRadioButtons] = useState({
    rows: "all-rows",
  });

  const [selectedColumns, setSelectedColumns] = useState([]);
  const [selectedRows, setSelectedRows] = useState("");

  const totalRows = datasetInfo.total_rows;

  useEffect(() => {
    if (open) {
      setInputError({ columns: "", rows: "" });
      setSelectedColumns(
        scopeInitialValues.columns.length === 0
          ? datasetColumns.map((column) => column.id)
          : scopeInitialValues.columns.map((index) => index - 1),
      );
      setSelectedRadioButtons({
        rows: scopeInitialValues.rows.length === 0 ? "all-rows" : "custom-rows",
      });
      setSelectedRows(
        scopeInitialValues.rows.length === 0
          ? ""
          : parseIndexToRange(scopeInitialValues.rows).join(","),
      );
    }
  }, [open, scopeInitialValues, datasetColumns]);

  const handleColumnSelection = (newSelection) => {
    setSelectedColumns(newSelection);
    setInputError((previousError) => ({
      ...previousError,
      columns: "",
    }));
  };

  const handleRadioChange = (event) => {
    setInputError((previousError) => ({
      ...previousError,
      rows: "",
    }));

    const value = event.target.value;
    setSelectedRadioButtons({
      rows: value,
    });
    setSelectedRows("");
  };

  const handleInputChange = (value) => {
    setSelectedRadioButtons({
      rows: "custom-rows",
    });

    try {
      parseRangeToIndex(value, totalRows);
      setInputError((previousError) => ({
        ...previousError,
        rows: "",
      }));
      setSelectedRows(value);
    } catch (error) {
      setInputError((previousError) => ({
        ...previousError,
        rows: error.message,
      }));
    }
  };

  const handleOnSave = () => {
    let errors = false;

    if (selectedColumns.length === 0) {
      setInputError((previousError) => ({
        ...previousError,
        columns: "Please select at least one column",
      }));
      errors = true;
    }

    if (selectedRadioButtons.rows === "custom-rows" && selectedRows === "") {
      setInputError((previousError) => ({
        ...previousError,
        rows: "Please specify the rows range",
      }));
      errors = true;
    }

    if (errors) {
      return;
    }

    const columnsArray =
      selectedColumns.length === datasetColumns.length
        ? []
        : selectedColumns.map((index) => index + 1);
    const rowsArray =
      selectedRadioButtons.rows === "all-rows"
        ? []
        : parseRangeToIndex(selectedRows, totalRows);

    const newScope = {
      columns: columnsArray,
      rows: rowsArray,
    };
    updateScope(newScope);
    setOpen(false);
  };

  return (
    <React.Fragment>
      <TooltipedCellItem
        key="edit-scope-button"
        icon={<ViewColumn />}
        label="Set scope"
        tooltip="Define scope"
        onClick={() => setOpen(true)}
      />
      {open && (
        <Dialog
          open={open}
          onClose={() => setOpen(false)}
          slotProps={{
            paper: {
              sx: {
                width: { md: 820, lg: 1000 },
                maxHeight: { lg: 700, xl: "auto" },
                maxWidth: 2000,
                transition: "width 0.3s ease, height 0.3s ease",
              },
            },
          }}
        >
          <DialogTitle>
            <Box display="flex" alignItems="center">
              <IconButton onClick={() => setOpen(false)}>
                <ArrowBackOutlined />
              </IconButton>
              <Typography variant="h5" sx={{ ml: 2 }}>
                {elementToConfigure} scope
              </Typography>
            </Box>
          </DialogTitle>
          <DialogContent>
            <Box sx={{ height: "100%", width: "100%" }}>
              <Stack spacing={4} sx={{ py: 2 }}>
                <Box>
                  <Typography variant="h6" sx={{ mb: 2 }}>
                    Columns
                  </Typography>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mb: 2 }}
                  >
                    Select the columns that will be transformed by this
                    converter. The selected columns will be used as input for
                    the conversion process.
                  </Typography>
                  {inputError.columns && (
                    <Box
                      sx={{
                        backgroundColor: "error.light",
                        color: "error.contrastText",
                        p: 2,
                        mx: 2,
                        my: 2,
                        borderRadius: 1,
                      }}
                    >
                      <Typography variant="body2">
                        {inputError.columns}
                      </Typography>
                    </Box>
                  )}
                  <DataGrid
                    rows={datasetColumns}
                    columns={columns}
                    checkboxSelection
                    onRowSelectionModelChange={handleColumnSelection}
                    rowSelectionModel={selectedColumns}
                    slots={{
                      toolbar: GridToolbar,
                    }}
                    slotProps={{
                      toolbar: {
                        showQuickFilter: true,
                      },
                    }}
                    initialState={{
                      pagination: {
                        paginationModel: { pageSize: 25 },
                      },
                    }}
                    sx={{
                      height: 300,
                      "& .MuiDataGrid-cell:focus": {
                        outline: "none",
                      },
                    }}
                  />
                </Box>

                <Box>
                  <Typography variant="h6" sx={{ mb: 2 }}>
                    Rows
                  </Typography>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mb: 2 }}
                  >
                    Select specific rows to be used for training the converter.
                    This allows you to focus on particular data patterns or
                    segments of your dataset.
                  </Typography>
                  <Box
                    sx={{
                      px: 2,
                      overflowY: "auto",
                      py: 4,
                      height: "auto",
                      width: "inherit",
                      transition: "opacity 0.3s ease",
                    }}
                  >
                    <RadioGroup
                      name="rows"
                      value={selectedRadioButtons.rows}
                      onChange={handleRadioChange}
                    >
                      <FormControlLabel
                        value="all-rows"
                        control={<Radio />}
                        label="Use all rows of the selected columns"
                        sx={{ my: 1 }}
                      />
                      <FormControlLabel
                        value="custom-rows"
                        control={<Radio />}
                        label="Specify the range from which this converter will learn"
                        sx={{ my: 1 }}
                      />
                      <InputWithDebounce
                        variant="outlined"
                        id="custom-rows"
                        label={"Row(s)"}
                        name={"rows"}
                        value={selectedRows}
                        onChange={(value) => handleInputChange(value)}
                        error={inputError["rows"] !== ""}
                        helperText={inputError["rows"]}
                        fullWidth
                        sx={{ mt: 2 }}
                      />
                    </RadioGroup>
                  </Box>
                </Box>
              </Stack>
            </Box>
          </DialogContent>
          <Box sx={{ p: 2, display: "flex", justifyContent: "flex-end" }}>
            <ButtonGroup>
              <Button onClick={() => setOpen(false)}>Back</Button>
              <Button
                variant="contained"
                onClick={handleOnSave}
                disabled={inputError.rows !== "" || inputError.columns !== ""}
              >
                Save
              </Button>
            </ButtonGroup>
          </Box>
        </Dialog>
      )}
    </React.Fragment>
  );
};

ConverterScopeModal.propTypes = {
  elementToConfigure: PropTypes.string,
  updateScope: PropTypes.func.isRequired,
  scopeInitialValues: PropTypes.shape({
    columns: PropTypes.arrayOf(PropTypes.number),
    rows: PropTypes.arrayOf(PropTypes.number),
  }).isRequired,
  datasetInfo: PropTypes.shape({
    total_columns: PropTypes.number,
    total_rows: PropTypes.number,
  }),
  datasetColumns: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      columnName: PropTypes.string.isRequired,
      valueType: PropTypes.string.isRequired,
      dataType: PropTypes.string.isRequired,
    }),
  ).isRequired,
};

export default ConverterScopeModal;
