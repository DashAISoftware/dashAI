// DatasetSummaryTable.js
import React, { useEffect, useState } from "react";
import { useSnackbar } from "notistack";
import {
  MaterialReactTable,
  useMaterialReactTable,
} from "material-react-table";
import { MRT_Localization_ES } from "material-react-table/locales/es";
import { MRT_Localization_EN } from "material-react-table/locales/en";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import {
  getDatasetSampleByFilePath as getDatasetSampleRequest,
  getDatasetTypesByFilePath as getDatasetTypesRequest,
} from "../../../api/datasets";
import { Box, CircularProgress } from "@mui/material";

function DatasetSummaryTableContent({ rows, columns, localization, theme }) {
  const table = useMaterialReactTable({
    columns,
    data: rows,
    mrtTheme: { baseBackgroundColor: theme.palette.ui.panelDark },
    muiTablePaperProps: { elevation: 0 },
    localization,
    initialState: { density: "compact" },
    enablePagination: false,
    enableTopToolbar: false,
    enableBottomToolbar: false,
    enableColumnActions: false,
    enableSorting: false,
  });

  return <MaterialReactTable table={table} />;
}

function DatasetSummaryTable({ file }) {
  const [loading, setLoading] = useState(true);
  const { enqueueSnackbar } = useSnackbar();
  const [rows, setRows] = useState([]);
  const [columns, setColumns] = useState([]);
  const theme = useTheme();
  const { i18n } = useTranslation();
  const localization = i18n.language.startsWith("es")
    ? MRT_Localization_ES
    : MRT_Localization_EN;

  const getDatasetInfo = async () => {
    setLoading(true);
    try {
      const dataset = await getDatasetSampleRequest(file);
      const types = await getDatasetTypesRequest(file);

      // Create MRT columns
      const gridColumns = [
        {
          accessorKey: "rowLabel",
          header: "",
          size: 150,
          enableSorting: false,
        },
      ];
      Object.keys(dataset).forEach((col) => {
        gridColumns.push({
          accessorKey: col,
          header: col,
          grow: 1,
          minSize: 150,
          enableSorting: false,
        });
      });

      // Build rows: 1 row for column type, 1 for data type, 1 for sample
      const typeRow = { rowLabel: "Column Type" };
      const dtypeRow = { rowLabel: "Data Type" };
      const sampleRow = { rowLabel: "Example" };

      Object.keys(dataset).forEach((col) => {
        typeRow[col] = types[col]?.type ?? "";
        dtypeRow[col] = types[col]?.dtype ?? "";
        sampleRow[col] = dataset[col]?.[0] ?? "";
      });

      setColumns(gridColumns);
      setRows([typeRow, dtypeRow, sampleRow]);
    } catch (error) {
      enqueueSnackbar("Error while trying to obtain the dataset.", {
        variant: "error",
      });
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    getDatasetInfo();
  }, []);

  return (
    <Box>
      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", p: 3 }}>
          <CircularProgress />
        </Box>
      ) : (
        <DatasetSummaryTableContent
          rows={rows}
          columns={columns}
          localization={localization}
          theme={theme}
        />
      )}
    </Box>
  );
}

export default DatasetSummaryTable;
