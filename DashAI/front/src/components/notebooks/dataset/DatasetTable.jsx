// src/components/common/ServerDataGrid.jsx
import { useEffect, useMemo, useState } from "react";
import {
  DataGrid,
  GridToolbarContainer,
  GridToolbarColumnsButton,
  GridToolbarFilterButton,
  GridToolbarDensitySelector,
  useGridApiContext,
} from "@mui/x-data-grid";
import { Button, Menu, MenuItem, Typography } from "@mui/material";
import { Download } from "@mui/icons-material";
import { LinearProgress } from "@mui/material";
import {
  exportDatasetCsvByPath,
  getDatasetTypesByFilePath,
} from "../../../api/datasets";

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
  const [columnTypes, setColumnTypes] = useState({});

  const [paginationModel, setPaginationModel] = useState({
    page: 0,
    pageSize: initialPageSize,
  });

  useEffect(() => {
    if (!datasetPath) return;
    const fetchColumnTypes = async () => {
      try {
        const types = await getDatasetTypesByFilePath(datasetPath);
        setColumnTypes(types);
      } catch (e) {
        console.error("Error fetching column types:", e);
      }
    };

    fetchColumnTypes();
  }, [datasetPath]);

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
        renderHeader: () => (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              textAlign: "center",
              width: "100%",
            }}
          >
            <Typography variant="subtitle2" style={{ fontWeight: "bold" }}>
              {field}
            </Typography>
            <Typography
              variant="caption"
              color="text.secondary"
              style={{ fontSize: "0.7rem" }}
            >
              {columnTypes[field]?.type || "unknown"}
            </Typography>
            {columnTypes[field]?.dtype && (
              <Typography
                variant="caption"
                color="text.secondary"
                style={{ fontSize: "0.7rem", opacity: 0.8 }}
              >
                {columnTypes[field]?.dtype}
              </Typography>
            )}
          </div>
        ),
      }));
  }, [rows, columnsProp, columnTypes]);

  // Custom CSV Export Button
  function CsvExportButton() {
    const [anchorEl, setAnchorEl] = useState(null);
    const open = Boolean(anchorEl);

    const handleClick = (event) => {
      setAnchorEl(event.currentTarget);
    };

    const handleClose = () => {
      setAnchorEl(null);
    };

    const handleExportCsv = async () => {
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
      } finally {
        handleClose();
      }
    };

    return (
      <>
        <Button
          size="small"
          startIcon={<Download />}
          onClick={handleClick}
          aria-controls={open ? "export-menu" : undefined}
          aria-haspopup="true"
          aria-expanded={open ? "true" : undefined}
        >
          Export
        </Button>
        <Menu
          id="export-menu"
          anchorEl={anchorEl}
          open={open}
          onClose={handleClose}
          MenuListProps={{
            "aria-labelledby": "export-button",
          }}
        >
          <MenuItem onClick={handleExportCsv}>
            <Download sx={{ mr: 1, fontSize: 16 }} />
            Download as CSV
          </MenuItem>
        </Menu>
      </>
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
      columnHeaderHeight={85}
      {...props}
    />
  );
}
