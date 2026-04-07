import React, { useState, useEffect, useMemo } from "react";
import { MaterialReactTable, useMaterialReactTable } from "material-react-table";
import { MRT_Localization_ES } from "material-react-table/locales/es";
import { MRT_Localization_EN } from "material-react-table/locales/en";
import { useTheme } from "@mui/material/styles";
import PropTypes from "prop-types";
import {
  Box,
  IconButton,
  Typography,
  Button,
  Dialog,
  DialogContent,
  DialogTitle,
  Stack,
} from "@mui/material";
import { ArrowBackOutlined, ViewColumn } from "@mui/icons-material";
import { getDatasetTypes } from "../../../api/datasets";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";

/**
 * Modal to select a class column for supervised learning
 * @param {Object} props
 * @param {Function} props.updateClassColumn - Function to update the selected class column
 * @param {number} props.classColumnInitialValue - Initial value of the class column index
 * @param {number} props.datasetId - ID of the dataset
 */
const ConverterClassColumnModal = ({
  updateClassColumn,
  classColumnInitialValue = null,
  datasetId,
}) => {
  const { i18n } = useTranslation();
  const theme = useTheme();
  const localization = i18n.language.startsWith("es")
    ? MRT_Localization_ES
    : MRT_Localization_EN;

  const columns = useMemo(
    () => [
      {
        accessorKey: "columnName",
        header: "Column Name",
        flex: 1,
      },
      {
        accessorKey: "valueType",
        header: "Value Type",
        flex: 0.5,
      },
      {
        accessorKey: "dataType",
        header: "Data Type",
        flex: 0.5,
      },
    ],
    [],
  );

  const toMRT = (id) => (id !== null ? { [String(id)]: true } : {});
  const fromMRT = (sel) => {
    const keys = Object.keys(sel).filter((k) => sel[k]);
    return keys.length > 0 ? Number(keys[0]) : null;
  };

  const [open, setOpen] = useState(false);
  const [selectedColumn, setSelectedColumn] = useState(null);
  const [datasetColumns, setDatasetColumns] = useState([]);
  const [loading, setLoading] = useState(false);
  const { enqueueSnackbar } = useSnackbar();

  useEffect(() => {
    if (open) {
      setSelectedColumn(classColumnInitialValue - 1);
      fetchDatasetColumns();
    }
  }, [open, classColumnInitialValue]);

  const fetchDatasetColumns = async () => {
    setLoading(true);
    try {
      const types = await getDatasetTypes(datasetId);
      const rowsArray = Object.keys(types).map((name, idx) => ({
        id: idx,
        columnName: name,
        valueType: types[name].type,
        dataType: types[name].dtype,
      }));
      setDatasetColumns(rowsArray);
    } catch (error) {
      enqueueSnackbar("Error while trying to obtain the dataset columns.");
      if (error.response) {
        console.error("Response error:", error.message);
      } else if (error.request) {
        console.error("Request error", error.request);
      } else {
        console.error("Unknown Error", error.message);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleColumnSelection = (updaterOrValue) => {
    const newMRTSelection =
      typeof updaterOrValue === "function"
        ? updaterOrValue(toMRT(selectedColumn))
        : updaterOrValue;
    setSelectedColumn(fromMRT(newMRTSelection));
  };

  const classTable = useMaterialReactTable({
    columns,
    data: datasetColumns,
    enableRowSelection: true,
    enableMultiRowSelection: false,
    onRowSelectionChange: handleColumnSelection,
    state: { rowSelection: toMRT(selectedColumn), isLoading: loading },
    getRowId: (row) => String(row.id),
    enableGlobalFilter: true,
    enableColumnFilters: false,
    enableSorting: true,
    enablePagination: true,
    muiPaginationProps: { rowsPerPageOptions: [25, 50] },
    initialState: { pagination: { pageSize: 25, pageIndex: 0 } },
    localization,
  });

  const handleOnSave = () => {
    if (selectedColumn === null) {
      return;
    }
    updateClassColumn(selectedColumn + 1);
    setOpen(false);
  };

  return (
    <React.Fragment>
      <Button
        startIcon={<ViewColumn />}
        onClick={() => setOpen(true)}
        variant="outlined"
        size="small"
        sx={{
          mr: 1,
          color: classColumnInitialValue === null ? "error.main" : "inherit",
          borderColor:
            classColumnInitialValue === null ? "error.main" : "inherit",
          "&:hover": {
            borderColor:
              classColumnInitialValue === null ? "error.main" : "inherit",
            backgroundColor:
              classColumnInitialValue === null ? "error.light" : "inherit",
          },
        }}
      >
        Set column
      </Button>
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
                Set column
              </Typography>
            </Box>
          </DialogTitle>
          <DialogContent>
            <Box sx={{ height: "100%", width: "100%" }}>
              <Stack spacing={4} sx={{ py: 2 }}>
                <Box>
                  <Typography variant="h6" sx={{ mb: 2 }}>
                    Class/Target Column
                  </Typography>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mb: 2 }}
                  >
                    Select one column to be used as the target variable for
                    supervised learning.
                  </Typography>
                  <MaterialReactTable table={classTable} />
                </Box>
              </Stack>
            </Box>
          </DialogContent>
          <Box sx={{ p: 2, display: "flex", justifyContent: "flex-end" }}>
            <Button onClick={() => setOpen(false)} sx={{ mr: 2 }}>
              Back
            </Button>
            <Button
              variant="contained"
              onClick={handleOnSave}
              disabled={selectedColumn === null}
            >
              Save
            </Button>
          </Box>
        </Dialog>
      )}
    </React.Fragment>
  );
};

ConverterClassColumnModal.propTypes = {
  updateClassColumn: PropTypes.func.isRequired,
  classColumnInitialValue: PropTypes.number,
  datasetId: PropTypes.number.isRequired,
};

export default ConverterClassColumnModal;
