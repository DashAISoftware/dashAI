import React, { useCallback, useState, useEffect } from "react";
import { DataGrid } from "@mui/x-data-grid";
import { Grid, Typography } from "@mui/material";
import DeleteItemModal from "../custom/DeleteItemModal";
import ConverterEditorModal from "./converterModals/ConverterEditorModal";
import PropTypes from "prop-types";
import ConverterScopeModal from "./converterModals/ConverterScopeModal";
import { getDatasetInfo as getDatasetInfoRequest } from "../../api/datasets";
import { parseIndexToRange } from "../../utils/parseRange";
import ConverterChainModal from "./converterModals/ConverterChainModal";

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

          // If the converter is a chain, filter its content recursively
          if (
            converter.name === "ConverterChain" &&
            Array.isArray(converter.params.steps)
          ) {
            converter.params.steps = removeById(
              converter.params.steps,
              idToRemove,
            );
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

        // If the converter is a Chain, recursively update its steps
        if (
          converter.name === "ConverterChain" &&
          Array.isArray(converter.params.steps)
        ) {
          return {
            ...converter,
            params: { steps: updateChainParams(converter.params.steps) },
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
            columns.length > 0
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
            rows.length > 0 ? parseIndexToRange(rows).join(", ") : "All rows";
          return <Typography variant="p">{rowsLabel}</Typography>;
        },
      },
      {
        field: "actions",
        type: "actions",
        minWidth: 150,
        getActions: (params) =>
          [
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
            <ConverterChainModal
              key="chain-component"
              converters={convertersToApply}
              setConvertersToApply={setConvertersToApply}
              existingChains={convertersToApply.filter(
                (converter) => converter.name === "ConverterChain",
              )}
              converterToAdd={params.row}
            />,
            <DeleteItemModal
              key="delete-component"
              deleteFromTable={createDeleteHandler(params.id)}
            />,
          ].filter((action) => {
            if (params.row.name === "ConverterChain") {
              // Chains doesn't have hyperparameters and can't be added to another chain
              return (
                action.key !== "edit-component" &&
                action.key !== "chain-component"
              );
            }
            let existingChains = convertersToApply.filter(
              (converter) => converter.name === "ConverterChain",
            );
            let existsChains = existingChains.length > 0;
            let inChain = existingChains.some((chain) => {
              return chain.params.steps.some(
                (step) => step.id === params.row.id,
              );
            });
            // Hide chain component if there are not chains
            if (!existsChains) {
              return action.key !== "chain-component";
            }
            // Hide scope component if the converter is already in a chain
            if (inChain) {
              return action.key !== "scope-component";
            }
            return true;
          }),
      },
    ],
    [createDeleteHandler],
  );

  const rows = React.useMemo(() => {
    const result = [];
    convertersToApply.forEach((converter, index) => {
      result.push({
        id: converter.id,
        order: index + 1,
        name: converter.name,
        params: converter.params,
        scope: converter.scope,
      });

      if (
        converter.name === "ConverterChain" &&
        Array.isArray(converter.params.steps)
      ) {
        converter.params.steps.forEach((step, stepIndex) => {
          result.push({
            id: step.id,
            order: `${index + 1}.${stepIndex + 1}`,
            name: step.name,
            params: step.params,
            scope: step.scope,
          });
        });
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
