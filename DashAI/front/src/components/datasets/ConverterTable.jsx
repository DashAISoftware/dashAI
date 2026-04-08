import React, { useCallback, useState, useEffect } from "react";
import {
  MaterialReactTable,
  useMaterialReactTable,
} from "material-react-table";
import { MRT_Localization_ES } from "material-react-table/locales/es";
import { MRT_Localization_EN } from "material-react-table/locales/en";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import { Box, Grid, Typography } from "@mui/material";
import DeleteItemModal from "../custom/DeleteItemModal";
import ConverterEditorModal from "./converterModals/ConverterEditorModal";
import PropTypes from "prop-types";
import ConverterScopeModal from "./converterModals/ConverterScopeModal";
import {
  getDatasetInfo as getDatasetInfoRequest,
  getDatasetSample,
  getDatasetTypes,
} from "../../api/datasets";
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
  const [datasetColumns, setDatasetColumns] = useState([]);
  const [loading, setLoading] = useState(true);
  const { enqueueSnackbar } = useSnackbar();
  const { i18n } = useTranslation();
  const theme = useTheme();
  const localization = i18n.language.startsWith("es")
    ? MRT_Localization_ES
    : MRT_Localization_EN;

  const getDatasetInfo = async () => {
    setLoading(true);
    try {
      const [dataset, types, info] = await Promise.all([
        getDatasetSample(datasetId),
        getDatasetTypes(datasetId),
        getDatasetInfoRequest(datasetId),
      ]);

      const rowsArray = Object.keys(dataset).map((name, idx) => ({
        id: idx,
        columnName: name,
        valueType: types[name].type,
        dataType: types[name].dtype,
      }));

      setDatasetColumns(rowsArray);
      setDatasetInfo({ ...info, id: datasetId });
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
        accessorKey: "order",
        header: "Order",
        minSize: 50,
        enableSorting: true,
      },
      {
        accessorKey: "name",
        header: "Converter",
        minSize: 250,
        enableSorting: false,
        Cell: ({ row }) => (
          <Grid container>
            <Grid size={{ xs: 12 }}>
              <Typography>{row.original.name}</Typography>
            </Grid>
          </Grid>
        ),
      },
      {
        id: "columns",
        header: "Columns",
        minSize: 100,
        enableSorting: false,
        enableColumnFilter: false,
        accessorFn: (row) => row.scope.columns,
        Cell: ({ row }) => {
          const cols = row.original.scope.columns;
          const columnsLabel = row.original.isStepInChain
            ? "-"
            : cols.length > 0
              ? parseIndexToRange(cols).join(", ")
              : "All columns";
          return <Typography variant="p">{columnsLabel}</Typography>;
        },
      },
      {
        id: "rows",
        header: "Rows",
        minSize: 100,
        enableSorting: false,
        enableColumnFilter: false,
        accessorFn: (row) => row.scope.rows,
        Cell: ({ row }) => {
          const scopeRows = row.original.scope.rows;
          const rowsLabel = row.original.isStepInChain
            ? "-"
            : scopeRows.length > 0
              ? parseIndexToRange(scopeRows).join(", ")
              : "All rows";
          return <Typography variant="p">{rowsLabel}</Typography>;
        },
      },
      {
        id: "actions",
        header: "Actions",
        minSize: 150,
        enableSorting: false,
        enableColumnFilter: false,
        Cell: ({ row }) => {
          const actions = [
            <ConverterEditorModal
              key="edit-component"
              converterToConfigure={row.original.name}
              updateParameters={handleUpdateParams(row.original.id)}
              paramsInitialValues={row.original.params}
            />,
            !row.original.isStepInChain && (
              <ConverterScopeModal
                key="scope-component"
                elementToConfigure={row.original.name}
                updateScope={handleUpdateScope(row.original.id)}
                scopeInitialValues={row.original.scope}
                datasetInfo={datasetInfo}
                datasetColumns={datasetColumns}
              />
            ),
            <DeleteItemModal
              key="delete-component"
              deleteFromTable={createDeleteHandler(row.original.id)}
            />,
          ].filter(Boolean);
          return <Box sx={{ display: "flex", gap: 0.5 }}>{actions}</Box>;
        },
      },
    ],
    [createDeleteHandler, datasetInfo, datasetColumns],
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

  const table = useMaterialReactTable({
    columns,
    data: rows,
    mrtTheme: { baseBackgroundColor: theme.palette.ui.panelDark },
    muiTablePaperProps: { elevation: 0 },
    localization,
    initialState: { density: "compact" },
    state: { isLoading: loading },
  });

  return <MaterialReactTable table={table} />;
};

ConverterTable.propTypes = {
  datasetId: PropTypes.number.isRequired,
  convertersToApply: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      name: PropTypes.string.isRequired,
      params: PropTypes.object.isRequired,
      scope: PropTypes.object.isRequired,
    }),
  ).isRequired,
  setConvertersToApply: PropTypes.func.isRequired,
};

export default ConverterTable;
