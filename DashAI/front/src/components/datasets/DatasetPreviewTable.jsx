// DatasetPreviewTable.js
import React, { useEffect, useMemo, useState } from "react";
import { useSnackbar } from "notistack";
import PropTypes from "prop-types";
import { DataGrid, useGridApiRef } from "@mui/x-data-grid";
import {
  getDatasetSample as getDatasetSampleRequest,
  getDatasetTypes as getDatasetTypesRequest,
} from "../../api/datasets";
import { dataTypesList, columnTypesList } from "../../utils/typesLists";
import SelectTypeCell from "../custom/SelectTypeCell";

function DatasetPreviewTable({
  previewData,
  isEditable,
  columnsSpec,
  setColumnsSpec,
}) {
  const [loading, setLoading] = useState(true);
  const { enqueueSnackbar } = useSnackbar();
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
          columnType: columnInfo.type,
          dataType: columnInfo.dtype,
        };
      });

      // const newColumnsSpec = {};
      // for (const columnName of columnNames) {
      //   const columnInfo = previewData.schema[columnName];
      //   newColumnsSpec[columnName] = {
      //     type: columnInfo.type,
      //     dtype: columnInfo.dtype,
      //   };
      // }

      // setColumnsSpec(newColumnsSpec);
      setLoading(false);
      setRows(rows);
    }
  }, [previewData]);


  const updateCellValue = async (id, field, newValue) => {
    await apiRef.current.setEditCellValue({ id, field, value: newValue });
    apiRef.current.stopCellEditMode({ id, field });
    setRows((prevRows) =>
      prevRows.map((row) =>
        row.id === id ? { ...row, [field]: newValue } : row,
      ),
    );

    const columnName = rows.find((row) => row.id === id)?.columnName;
    console.log("ucv columnName:", columnName);
    const updateColumns = { ...columnsSpec };
    console.log("ucv updateColumns:", updateColumns);
    console.log("ucv field:", field);
    if (field === "dataType") {
      updateColumns[columnName].dtype = newValue;
    } else if (field === "columnType") {
      updateColumns[columnName].type = newValue;
    }

    setColumnsSpec(updateColumns);

    console.log(`Columna ${columnName} actualizada:`, {
      field,
      newValue,
      currentSpec: updateColumns[columnName]
    });
  };

  const renderSelectCell = (params, options) => {
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
      renderEditCell: (params) =>
        isEditable && renderSelectCell(params, columnTypesList),
      minWidth: 200,
      editable: isEditable,
    },
    {
      field: "dataType",
      headerName: "Data type",
      renderEditCell: (params) =>
        isEditable && renderSelectCell(params, dataTypesList),
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
