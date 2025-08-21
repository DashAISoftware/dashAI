// src/components/common/ServerDataGrid.jsx
import { useEffect, useMemo, useState } from "react";
import {
  DataGrid,
  GridToolbarContainer,
  GridToolbarColumnsButton,
  GridToolbarFilterButton,
  GridToolbarDensitySelector,
  useGridApiContext,
  gridFilteredSortedRowIdsSelector,
  gridVisibleColumnFieldsSelector,
} from "@mui/x-data-grid";
import { Button } from "@mui/material";
import { Download } from "@mui/icons-material";
import { LinearProgress } from "@mui/material";
import { exportDatasetCsvByPath } from "../../api/datasets";

/**
 * Props:
 * - fetchPage: async (page, pageSize) => { rows: Array<object>, total: number }
 * - initialPageSize?: number (default 5)
 * - columns?: GridColDef[] (optional)
 * - deps?: any[] (optional)
 * - autoHeight?: boolean (default true)
 * - pageSizeOptions?: number[] (default [5, 10, 25])
 * - datasetPath?: string (optional) - Path to dataset for CSV export
 */
export default function DatasetTable({
  fetchPage,
  initialPageSize = 5,
  columns: columnsProp,
  deps = [],
  autoHeight = true,
  density = "compact",
  pageSizeOptions = [5, 10, 25],
  datasetPath, // Nueva prop para la ruta del dataset
  ...props
}) {
  const [rows, setRows] = useState([]);
  const [rowCount, setRowCount] = useState(0);
  const [loading, setLoading] = useState(false);

  const [paginationModel, setPaginationModel] = useState({
    page: 0,
    pageSize: initialPageSize,
  });

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        setLoading(true);
        const { page, pageSize } = paginationModel;
        const data = await fetchPage(page, pageSize);
        if (!alive) return;

        const withIds = (data?.rows ?? []).map((r, i) => ({
          id: page * pageSize + i,
          ...r,
        }));

        setRows(withIds);
        setRowCount(data?.total ?? withIds.length);
      } catch (e) {
        console.error(e);
        setRows([]);
        setRowCount(0);
      } finally {
        if (alive) setLoading(false);
      }
    };
    load();
    return () => {
      alive = false;
    };
  }, [fetchPage, paginationModel, ...deps]);

  useEffect(() => {
    setPaginationModel((m) => ({ ...m, page: 0 }));
  }, deps);

  const columns = useMemo(() => {
    if (columnsProp?.length) return columnsProp;
    const first = rows[0];
    if (!first) return [];
    return Object.keys(first)
      .filter((k) => k !== "id")
      .map((field) => ({
        field,
        headerName: field,
        flex: 1,
        minWidth: 120,
      }));
  }, [rows, columnsProp]);

  // Custom CSV Export Button
  function CsvExportButton() {
    const handleExport = async () => {
      try {
        if (datasetPath) {
          // Usar nuestro endpoint personalizado
          const blob = await exportDatasetCsvByPath(datasetPath);

          // Crear URL temporal y descargar
          const url = window.URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.href = url;

          // Extraer nombre del dataset desde la ruta
          const datasetName = datasetPath.split("/").pop() || "dataset";
          link.download = `${datasetName}.csv`;

          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          window.URL.revokeObjectURL(url);
        } else {
          // Fallback al método original del DataGrid
          const apiRef = useGridApiContext();
          apiRef.current.exportDataAsCsv({
            fileName: "dataset-export",
            delimiter: ",",
            utf8WithBom: true,
          });
        }
      } catch (error) {
        console.error("Error exporting CSV:", error);
        // Fallback al método original en caso de error
        const apiRef = useGridApiContext();
        apiRef.current.exportDataAsCsv({
          fileName: "dataset-export",
          delimiter: ",",
          utf8WithBom: true,
        });
      }
    };

    return (
      <Button size="small" startIcon={<Download />} onClick={handleExport}>
        Export CSV
      </Button>
    );
  }

  // Custom toolbar with CSV-only export
  function CustomToolbar() {
    return (
      <GridToolbarContainer>
        <GridToolbarColumnsButton />
        <GridToolbarFilterButton />
        <GridToolbarDensitySelector />
        <CsvExportButton />
      </GridToolbarContainer>
    );
  }

  return (
    <DataGrid
      rows={rows}
      columns={columns}
      rowCount={rowCount}
      loading={loading}
      autoHeight={autoHeight}
      disableRowSelectionOnClick
      paginationMode="server"
      paginationModel={paginationModel}
      onPaginationModelChange={setPaginationModel}
      pageSizeOptions={pageSizeOptions}
      density={density}
      slots={{
        toolbar: CustomToolbar,
        loadingOverlay: LinearProgress,
      }}
      {...props}
    />
  );
}
