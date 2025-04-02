import React, { useCallback, useState, useEffect } from "react";
import { DataGrid } from "@mui/x-data-grid";
import { Grid, Typography } from "@mui/material";
import DeleteItemModal from "../custom/DeleteItemModal";
import ConverterEditorModal from "./converterModals/ConverterEditorModal";
import PropTypes from "prop-types";
import ConverterScopeModal from "./converterModals/ConverterScopeModal";
import { getDatasetInfo as getDatasetInfoRequest } from "../../api/datasets";
import { parseIndexToRange } from "../../utils/parseRange";
import { useSnackbar } from "notistack";
/**
 * Table to display and manage the list of converters to apply to a dataset
 * @param {Object} props
 * @param {number} props.datasetId - ID of the dataset
 * @param {Array} props.convertersToApply - List of converters to apply
 * @param {Function} props.setConvertersToApply - Function to update the list of converters to apply
 */
const ConverterTable = ({
  datasetId,
  convertersToApply,
  setConvertersToApply,
}) => {
  const [datasetInfo, setDatasetInfo] = useState({});
  const [loading, setLoading] = useState(true);
  const { enqueueSnackbar } = useSnackbar();

  const getDatasetInfo = async () => {
    setLoading(true);
    try {
      const datasetInfo = await getDatasetInfoRequest(datasetId);
      setDatasetInfo({ ...datasetInfo, id: datasetId });
    } catch (error) {
      enqueueSnackbar("Error while trying to obtain the dataset info.");
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

  useEffect(() => {
    getDatasetInfo();
  }, []);

  const createDeleteHandler = useCallback(
    (id) => () => {
      const removeById = (convertersArray, idToRemove) => {
        return convertersArray.filter((converter) => {
          // If the converter's id matches the id to remove, exclude it
          if (converter.id === idToRemove) {
            return false;
          }
          // Include the converter in the result
          return true;
        });
      };

      let updatedConverters = removeById(convertersToApply, id);
      setConvertersToApply(updatedConverters);
    },
    [convertersToApply],
  );

  const handleUpdateParams = (id) => (newParams) => {
    const updateChainParams = (converters) => {
      return converters.map((converter) => {
        // Check if the converter is the one we need to update
        if (converter.id === id) {
          return {
            ...converter,
            params: newParams,
          };
        }

        // If no update is needed, return the converter as is
        return converter;
      });
    };

    // Create a new copy of the convertersToApply with updated parameters
    const updatedConverters = updateChainParams(convertersToApply);

    // Update the state with the new converters
    setConvertersToApply(updatedConverters);
  };

  const handleUpdateScope = (id) => (newScope) => {
    // Converters that are not in a chain can be updated
    let index = convertersToApply.findIndex((converter) => converter.id === id);
    if (index !== -1) {
      let updatedConverters = [...convertersToApply];
      updatedConverters[index] = {
        ...updatedConverters[index],
        scope: newScope,
      };

      setConvertersToApply(updatedConverters);
      return;
    }
  };

  const columns = React.useMemo(
    () => [
      {
        field: "order",
        headerName: "Order",
        minWidth: 50,
        editable: false,
        sortable: true,
      },
      {
        field: "name",
        headerName: "Converter",
        minWidth: 250,
        editable: false,
        sortable: false,
        renderCell: ({ row }) => {
          return (
            <Grid container>
              <Grid item xs={12}>
                <Typography>{row.name}</Typography>
              </Grid>
            </Grid>
          );
        },
      },
      {
        field: `columns`,
        headerName: "Columns",
        minWidth: 100,
        editable: false,
        sortable: false,
        valueGetter: (params) => params.row.scope.columns,
        renderCell: ({ row }) => {
          const columns = row.scope.columns;
          const columnsLabel =
            row.isStepInChain
              ? "-"
              : columns.length > 0
              ? parseIndexToRange(columns).join(", ")
              : "All columns";
          return <Typography variant="p">{columnsLabel}</Typography>;
        },
      },
      {
        field: `rows`,
        headerName: "Rows",
        minWidth: 100,
        editable: false,
        sortable: false,
        valueGetter: (params) => params.row.scope.rows,
        renderCell: ({ row }) => {
          const rows = row.scope.rows;
          const rowsLabel =
            row.isStepInChain
              ? "-"
              : rows.length > 0
              ? parseIndexToRange(rows).join(", ")
              : "All rows";
          return <Typography variant="p">{rowsLabel}</Typography>;
        },
      },
      {
        field: "actions",
        type: "actions",
        minWidth: 150,
        getActions: (params) => [
          <ConverterEditorModal
            key="edit-component"
            converterToConfigure={params.row.name}
            updateParameters={handleUpdateParams(params.row.id)}
            paramsInitialValues={params.row.params}
          />,
          <ConverterScopeModal
            key="scope-component"
            elementToConfigure={params.row.name}
            updateScope={handleUpdateScope(params.row.id)}
            scopeInitialValues={params.row.scope}
            datasetInfo={datasetInfo}
          />,
          <DeleteItemModal
            key="delete-component"
            deleteFromTable={createDeleteHandler(params.id)}
          />,
        ].filter(
          // Filter Scope modal if the converter is after a chain
          (action, index) => {
            if (action.key === "scope-component") {
              return !params.row.isStepInChain;
            }
            return true;
          },

        ),
      },
    ],
    [createDeleteHandler],
  );

  const rows = React.useMemo(() => {
    const result = [];
    let currentOrder = 1;

    convertersToApply.forEach((converter, index) => {
      if (converter.name === "ConverterChain") {
        // Add the chain converter
        result.push({
          id: converter.id,
          order: currentOrder,
          name: converter.name,
          params: converter.params,
          scope: converter.scope,
          isStepInChain: false,
        });

        // Add the chained converters
        let steps = converter.params["steps"];
        for (let i = 1; i <= steps; i++) {
          const stepConverter = convertersToApply[index + i];
          if (stepConverter) {
            result.push({
              id: stepConverter.id,
              order: `${currentOrder}.${i}`,
              name: stepConverter.name,
              params: stepConverter.params,
              scope: stepConverter.scope,
              isStepInChain: true,
            });
          }
        }
        currentOrder++;
      } else {
        // Check if this converter is not a step in a chain
        const isStepInChain = convertersToApply.some(
          (c, i) =>
            c.name === "ConverterChain" &&
            i < index &&
            index <= i + c.params["steps"],
        );

        if (!isStepInChain) {
          result.push({
            id: converter.id,
            order: currentOrder,
            name: converter.name,
            params: converter.params,
            scope: converter.scope,
            isStepInChain: false,
          });
          currentOrder++;
        }
      }
    });
    return result;
  }, [convertersToApply]);

  return (
    <Grid container>
      {/* Selected converters table */}
      <Grid item xs={12}>
        <DataGrid
          rows={rows}
          columns={columns}
          initialState={{
            sorting: {
              sortModel: [{ field: "order", sort: "asc" }],
            },
            pagination: {
              paginationModel: {
                pageSize: 5,
              },
            },
          }}
          pageSize={5}
          pageSizeOptions={[5, 10]}
          disableRowSelectionOnClick
          autoHeight
          loading={loading}
        />
      </Grid>
    </Grid>
  );
};

ConverterTable.propTypes = {
  datasetId: PropTypes.number.isRequired,
  convertersToApply: PropTypes.arrayOf(PropTypes.object),
  setConvertersToApply: PropTypes.func,
};

ConverterTable.defaultProps = {
  convertersToApply: [],
  setConvertersToApply: () => {},
};

export default ConverterTable;
