// DatasetPreviewTable.js
import React, { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import { DataGrid, useGridApiRef } from "@mui/x-data-grid";
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
  const apiRef = useGridApiRef();

  useEffect(() => {
    if (previewData.sample && previewData.sample.length > 0) {
      const columnNames = Object.keys(previewData.schema);

      const rows = columnNames.map((name, idx) => {
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
      setRows(rows);
    }
  }, [previewData, columnsSpec]);

  const updateCellValue = async (id, field, newValue) => {
    await apiRef.current.setEditCellValue({ id, field, value: newValue });
    apiRef.current.stopCellEditMode({ id, field });
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

  const renderSelectCell = (params) => {
    let options = [];
    if (params.field === "dataType") {
      const column = rows.find((row) => row.id === params.id);
      const selectedColumnType = column?.columnType;
      options = dataTypesbyColumnType[selectedColumnType] || [];
    } else if (params.field === "columnType") {
      options = columnTypesList;
    }

    return (
      <SelectTypeCell
        id={params.id}
        value={params.value}
        field={params.field}
        options={options}
        updateValue={(id, field, newValue) =>
          updateCellValue(id, field, newValue)
        }
      />
    );
  };

  const columns = useMemo(() => [
    {
      field: "columnName",
      headerName: "Column name",
      minWidth: 200,
      editable: false,
    },
    {
      field: "example",
      headerName: "Example",
      minWidth: 200,
      editable: false,
    },
    {
      field: "columnType",
      headerName: "Column type",
      renderEditCell: (params) => isEditable && renderSelectCell(params),
      minWidth: 200,
      editable: isEditable,
    },
    {
      field: "dataType",
      headerName: "Data type",
      renderEditCell: (params) => isEditable && renderSelectCell(params),
      minWidth: 200,
      editable: isEditable,
    },
  ]);

  return (
    <DataGrid
      rows={rows}
      columns={columns}
      initialState={{
        pagination: {
          paginationModel: {
            pageSize: 4,
          },
        },
      }}
      pageSize={4}
      pageSizeOptions={[4, 5, 10]}
      loading={loading}
      apiRef={apiRef}
      autoHeight
    />
  );
}

DatasetPreviewTable.propTypes = {
  datasetId: PropTypes.number,
  isEditable: PropTypes.bool,
  columnsSpec: PropTypes.object,
  setColumnsSpec: PropTypes.func,
};

export default DatasetPreviewTable;
