// DatasetPreviewTable.js
import React, { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import { MaterialReactTable, useMaterialReactTable } from "material-react-table";
import { MRT_Localization_ES } from "material-react-table/locales/es";
import { MRT_Localization_EN } from "material-react-table/locales/en";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import { dataTypesbyColumnType, columnTypesList } from "../../utils/typesLists";
import SelectTypeCell from "../custom/SelectTypeCell";

function DatasetPreviewTable({
  previewData,
  isEditable,
  columnsSpec,
  setColumnsSpec,
}) {
  const [loading, setLoading] = useState(true);
  const [rows, setRows] = useState([]);
  const { i18n } = useTranslation();
  const theme = useTheme();
  const localization = i18n.language.startsWith("es")
    ? MRT_Localization_ES
    : MRT_Localization_EN;

  useEffect(() => {
    if (previewData.sample && previewData.sample.length > 0) {
      const columnNames = Object.keys(previewData.schema);

      const newRows = columnNames.map((name, idx) => {
        const columnInfo = previewData.schema[name];
        return {
          id: idx,
          columnName: name,
          example: previewData.sample[0][name],
          columnType: columnsSpec[name]?.type || columnInfo.type,
          dataType: columnsSpec[name]?.dtype || columnInfo.dtype,
        };
      });

      setLoading(false);
      setRows(newRows);
    }
  }, [previewData, columnsSpec]);

  const updateCellValue = (id, field, newValue) => {
    setRows((prevRows) =>
      prevRows.map((row) => {
        if (row.id === id) {
          if (field === "columnType") {
            const baseDataType = dataTypesbyColumnType[newValue]?.[0] || "";
            return { ...row, columnType: newValue, dataType: baseDataType };
          }
          if (field === "dataType") {
            return { ...row, dataType: newValue };
          }
        }
        return row;
      }),
    );

    const columnName = rows.find((row) => row.id === id)?.columnName;
    const updateColumns = { ...columnsSpec };
    if (field === "columnType") {
      updateColumns[columnName].type = newValue;
      updateColumns[columnName].dtype =
        dataTypesbyColumnType[newValue]?.[0] || "";
    } else if (field === "dataType") {
      updateColumns[columnName].dtype = newValue;
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
        Cell: ({ row }) => {
          const options =
            dataTypesbyColumnType[row.original.columnType] || [];
          return isEditable ? (
            <SelectTypeCell
              id={row.original.id}
              value={row.original.dataType}
              field="dataType"
              options={options}
              updateValue={(id, field, newValue) =>
                updateCellValue(id, field, newValue)
              }
            />
          ) : (
            row.original.dataType
          );
        },
      },
    ],
    [isEditable, rows],
  );

  const table = useMaterialReactTable({
    columns,
    data: rows,
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

DatasetPreviewTable.propTypes = {
  datasetId: PropTypes.number,
  isEditable: PropTypes.bool,
  columnsSpec: PropTypes.object,
  setColumnsSpec: PropTypes.func,
};

export default DatasetPreviewTable;
