// DatasetSummaryTable.js
import React, { useEffect, useMemo, useState } from "react";
import { useSnackbar } from "notistack";
import PropTypes from "prop-types";
import {
  MaterialReactTable,
  useMaterialReactTable,
} from "material-react-table";
import { useTheme } from "@mui/material/styles";
import { useTableLocalization } from "../../utils/useTableLocalization";
import {
  getDatasetSample as getDatasetSampleRequest,
  getDatasetTypes as getDatasetTypesRequest,
} from "../../api/datasets";
import { dataTypesList, columnTypesList } from "../../utils/typesLists";
import SelectTypeCell from "../custom/SelectTypeCell";

function DatasetSummaryTable({
  datasetId,
  isEditable,
  columnsSpec,
  setColumnsSpec,
}) {
  const [loading, setLoading] = useState(true);
  const { enqueueSnackbar } = useSnackbar();
  const [rows, setRows] = useState([]);
  const theme = useTheme();
  const localization = useTableLocalization();

  const getDatasetInfo = async () => {
    setLoading(true);
    try {
      const dataset = await getDatasetSampleRequest(datasetId);
      const types = await getDatasetTypesRequest(datasetId);
      const rowsArray = Object.keys(dataset).map((name, idx) => {
        return {
          id: idx,
          columnName: name,
          example: dataset[name][0],
          columnType: types[name].type,
          dataType: types[name].dtype,
        };
      });
      setRows(rowsArray);
      if (isEditable) {
        setColumnsSpec(types);
      }
    } catch (error) {
      enqueueSnackbar("Error while trying to obtain the dataset.");
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

  const updateCellValue = (id, field, newValue) => {
    setRows((prevRows) =>
      prevRows.map((row) =>
        row.id === id ? { ...row, [field]: newValue } : row,
      ),
    );

    const columnName = rows.find((row) => row.id === id)?.columnName;
    const updateColumns = { ...columnsSpec };

    if (field === "dataType") {
      updateColumns[columnName].dtype = newValue;
    } else if (field === "columnType") {
      updateColumns[columnName].type = newValue;
    }

    setColumnsSpec(updateColumns);
  };

  const columns = useMemo(
    () => [
      {
        accessorKey: "columnName",
        header: "Column name",
        size: 200,
      },
      {
        accessorKey: "example",
        header: "Example",
        size: 200,
      },
      {
        accessorKey: "columnType",
        header: "Column type",
        size: 200,
        Cell: ({ row }) =>
          isEditable ? (
            <SelectTypeCell
              id={row.original.id}
              value={row.original.columnType}
              field="columnType"
              options={columnTypesList}
              updateValue={(id, field, newValue) =>
                updateCellValue(id, field, newValue)
              }
            />
          ) : (
            row.original.columnType
          ),
      },
      {
        accessorKey: "dataType",
        header: "Data type",
        size: 200,
        Cell: ({ row }) =>
          isEditable ? (
            <SelectTypeCell
              id={row.original.id}
              value={row.original.dataType}
              field="dataType"
              options={dataTypesList}
              updateValue={(id, field, newValue) =>
                updateCellValue(id, field, newValue)
              }
            />
          ) : (
            row.original.dataType
          ),
      },
    ],
    [isEditable, rows],
  );

  useEffect(() => {
    getDatasetInfo();
  }, []);

  const table = useMaterialReactTable({
    columns,
    data: rows,
    muiTableBodyCellProps: { sx: { whiteSpace: "pre" } },
    getRowId: (row) => String(row.id),
    state: { isLoading: loading },
    enableSorting: false,
    enableColumnFilters: false,
    enableGlobalFilter: false,
    enableDensityToggle: false,
    enableFullScreenToggle: false,
    enableHiding: false,
    initialState: {
      pagination: { pageIndex: 0, pageSize: 4 },
    },
    muiPaginationProps: {
      rowsPerPageOptions: [4, 5, 10],
    },
    localization,
  });

  return <MaterialReactTable table={table} />;
}

DatasetSummaryTable.propTypes = {
  datasetId: PropTypes.number,
  isEditable: PropTypes.bool,
  columnsSpec: PropTypes.object,
  setColumnsSpec: PropTypes.func,
};

export default DatasetSummaryTable;
