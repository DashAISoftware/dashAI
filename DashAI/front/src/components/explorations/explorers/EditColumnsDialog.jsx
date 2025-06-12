import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";

import {
  Dialog,
  DialogContent,
  DialogTitle,
  Box,
  IconButton,
  Typography,
  Chip,
  Stack,
} from "@mui/material";
import { DataGrid, GridToolbar } from "@mui/x-data-grid";
import { ArrowBackOutlined, ViewColumn } from "@mui/icons-material";

import TooltipedCellItem from "../../shared/TooltipedCellItem";

import { useSnackbar } from "notistack";

const columns = [
  {
    field: "id",
    headerName: "Index",
  },
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
  {
    field: "order",
    headerName: "Selected Order",
    type: "number",
    flex: 0.5,
  },
];

/**
 * Dialog to edit columns selection
 * @param {Object} props
 * @param {Array} props.datasetColumns List of columns
 * @param {Function} props.updateValue Callback to update the selected columns
 * @param {Array} props.initialValues Initial selected columns
 * @param {Object} props.explorerType Explorer type object with metadata
 */
function EditColumnsDialog({
  datasetColumns,
  updateValue,
  initialValues,
  explorerType,
}) {
  const { enqueueSnackbar } = useSnackbar();

  const [open, setOpen] = useState(false);
  const handleClose = () => {
    if (!isValidSelection(rowSelectionModel)) {
      enqueueSnackbar("Invalid selection, changes were not be saved", {
        variant: "warning",
      });
    }
    setOpen(false);
  };

  const explorer = explorerType?.value;
  const allowedDtypes = explorer?.metadata?.allowed_dtypes || [];
  const restrictedDtypes = explorer?.metadata?.restricted_dtypes || [];
  const inputCardinality = explorer?.metadata?.input_cardinality || {};
  const validColumns = explorerType?.validColumns || [];

  const [rows, setRows] = useState([]);
  useEffect(() => {
    if (datasetColumns) {
      const validColsId = new Set(validColumns.map((col) => col.id));
      const cols = datasetColumns.map((col) => {
        return {
          ...col,
          disabled: !validColsId.has(col.id),
          order: initialValues.find((row) => row.id === col.id)?.order || 0,
        };
      });
      setRows(cols);
    }
  }, [datasetColumns, explorerType, open]);

  const [rowSelectionModel, setRowSelectionModel] = useState([]);
  // update row selection model on initial values change or dialog open
  useEffect(() => {
    setRowSelectionModel(initialValues.map((params) => params.id));
  }, [initialValues, open]);

  const handleSelection = (selection) => {
    if (selection.length > inputCardinality.max) {
      selection = selection.slice(0, inputCardinality.max);
    }

    // update order for the rows
    let newRows = rows.map((row) => {
      const order = selection.indexOf(row.id) + 1;
      return { ...row, order };
    });
    setRows(newRows);
    setRowSelectionModel(selection);
    if (!isValidSelection(selection)) return;

    updateValue(
      newRows
        .filter((row) => selection.includes(row.id))
        .sort((a, b) => {
          return a.order - b.order;
        })
        .map((row) => {
          return {
            id: row.id,
            columnName: row.columnName,
            valueType: row.valueType,
            dataType: row.dataType,
            order: row.order,
          };
        }),
    );
  };

  const isRowSelectable = (params) => {
    // check if the row is already selected
    if (rowSelectionModel.includes(params.id)) {
      return true;
    }

    // check if the row is disabled
    if (params.row.disabled) {
      return false;
    }

    // check if the row selection model is at the maximum cardinality
    const selectedCount = rowSelectionModel.length;
    const maxReached =
      selectedCount >= inputCardinality.max ||
      selectedCount >= inputCardinality.exact;
    if (maxReached) {
      return false;
    }

    return true;
  };

  const isValidSelection = (selection) => {
    if (inputCardinality.exact && selection.length !== inputCardinality.exact) {
      return false;
    }

    if (inputCardinality.min && selection.length < inputCardinality.min) {
      return false;
    }

    if (inputCardinality.max && selection.length > inputCardinality.max) {
      return false;
    }

    return true;
  };

  return (
    <React.Fragment>
      <TooltipedCellItem
        key="edit-columns-button"
        icon={<ViewColumn />}
        label="Edit Columns"
        tooltip={`Edit column selection`}
        onClick={() => setOpen(true)}
      />

      {open && (
        <Dialog
          open={open}
          onClose={handleClose}
          PaperProps={{
            sx: {
              width: { md: 820, lg: 1000 },
              maxHeight: { lg: 700, xl: "auto" },
              maxWidth: 2000,
              transition: "width 0.3s ease, height 0.3s ease",
            },
          }}
        >
          <DialogTitle>
            <Box display="flex" alignItems="center">
              <IconButton onClick={handleClose}>
                <ArrowBackOutlined />
              </IconButton>
              <Typography variant="h5" sx={{ ml: 2 }}>
                Update Column Selection
              </Typography>
            </Box>
          </DialogTitle>
          <DialogContent>
            <Box sx={{ height: "100%", width: "100%" }}>
              <Typography
                variant="body1"
                sx={{ mb: 2, whiteSpace: "pre-line" }}
              >
                {`Select the columns you want to use for the ${explorerType.label} exploration`}
              </Typography>

              <Stack
                direction="row"
                spacing={1}
                sx={{ mb: 1, display: "flex", justifyContent: "space-evenly" }}
              >
                {inputCardinality.min && (
                  <Typography variant="body2">
                    Minimum number of columns: {inputCardinality.min}
                  </Typography>
                )}
                {inputCardinality.exact && (
                  <Typography variant="body2">
                    Number of columns required: {inputCardinality.exact}
                  </Typography>
                )}
                {inputCardinality.max && (
                  <Typography variant="body2">
                    Maximum number of columns: {inputCardinality.max}
                  </Typography>
                )}
              </Stack>

              {allowedDtypes?.length > 0 && !allowedDtypes.includes("*") && (
                <Box
                  sx={{
                    mb: 1,
                    display: "flex",
                    flexDirection: "row",
                    gap: 1,
                    alignItems: "center",
                  }}
                >
                  <Typography variant="body2">Allowed data types:</Typography>
                  {allowedDtypes.map((dtype) => (
                    <Chip
                      key={dtype}
                      label={dtype}
                      color="secondary"
                      size="small"
                    />
                  ))}
                </Box>
              )}
              {restrictedDtypes?.length > 0 && (
                <Box
                  sx={{
                    mb: 1,
                    display: "flex",
                    flexDirection: "row",
                    gap: 1,
                    alignItems: "center",
                  }}
                >
                  <Typography variant="body2">
                    Restricted data types:
                  </Typography>
                  {restrictedDtypes.map((dtype) => (
                    <Chip
                      key={dtype}
                      label={dtype}
                      color="error"
                      size="small"
                    />
                  ))}
                </Box>
              )}

              <DataGrid
                autoHeight
                rows={rows}
                columns={columns}
                initialState={{
                  pagination: {
                    paginationModel: {
                      pageSize: 5,
                    },
                  },
                  sorting: {
                    // sortModel: [
                    //   {
                    //     field: "order",
                    //     sort: "asc",
                    //   },
                    // ],
                  },
                }}
                pageSizeOptions={[5, 10, 20]}
                checkboxSelection
                onRowSelectionModelChange={handleSelection}
                rowSelectionModel={rowSelectionModel}
                isRowSelectable={isRowSelectable}
                density="compact"
                getRowClassName={(params) => {
                  if (isRowSelectable(params) === false) {
                    return "mui-row-disabled";
                  }
                  return "";
                }}
                sx={{
                  "& .mui-row-disabled": {
                    backgroundColor: "rgba(0, 0, 0, 0.12)",
                    color: "#777",
                  },
                }}
                slots={{
                  toolbar: GridToolbar,
                }}
                slotProps={{
                  toolbar: {
                    showQuickFilter: true,
                  },
                }}
              />
            </Box>
          </DialogContent>
        </Dialog>
      )}
    </React.Fragment>
  );
}

EditColumnsDialog.propTypes = {
  datasetColumns: PropTypes.array.isRequired,
  updateValue: PropTypes.func.isRequired,
  initialValues: PropTypes.array.isRequired,
  explorerType: PropTypes.object.isRequired,
};

export default EditColumnsDialog;
