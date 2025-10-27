// src/components/common/ServerDataGrid.jsx
import { useEffect, useMemo, useState, useCallback } from "react";
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
  getDatasetFileFiltered,
} from "../../../api/datasets";

/**
 * Props:
 * - fetchPage: async (page, pageSize, filterModel) => { rows: Array<object>, total: number }
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
  pageSizeOptions = [5, 10, 25],
  datasetPath,
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
  const [filterModel, setFilterModel] = useState({ items: [] });

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
        const data = await fetchPage(page, pageSize, filterModel);
        if (!alive) return;

        const withIds = (data?.rows ?? []).map((r, i) => ({
          id: page * pageSize + i,
          ...r,
        }));

        setRows(withIds);
        // Siempre usa el total devuelto por el backend para la paginación
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
  }, [fetchPage, paginationModel, filterModel, ...deps]);
  // Handler for DataGrid filter changes
  // Evita que el filtro se borre si no hay resultados
  // Siempre que cambie el filtro, resetea la paginación a la página 0
  const handleFilterModelChange = useCallback((model) => {
    setFilterModel((prev) => {
      // Si el filtro es igual al anterior, igual resetea la paginación
      setPaginationModel((m) => ({ ...m, page: 0 }));
      if (!model || !model.items || model.items.length === 0) {
        return { items: [] };
      }
      return model;
    });
  }, []);

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
        type:
          columnTypes[field] &&
          ["int", "integer", "float", "double", "number"].includes(
            String(columnTypes[field].type).toLowerCase(),
          )
            ? "number"
            : columnTypes[field] &&
                ["bool", "boolean"].includes(
                  String(columnTypes[field].type).toLowerCase(),
                )
              ? "boolean"
              : columnTypes[field] &&
                  ["date", "datetime", "timestamp"].includes(
                    String(columnTypes[field].type).toLowerCase(),
                  )
                ? "date"
                : "string",
        minWidth: 120,
        width: Math.max(120, field.length * 8 + 40),
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
          slotProps={{
            list: {
              "aria-labelledby": "export-button",
            },
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

  // DEBUG: Log filterModel changes para ver qué se envía al backend
  useEffect(() => {
    if (filterModel && filterModel.items && filterModel.items.length > 0) {
      // Solo loguea si hay filtros activos
      console.log("[DEBUG filterModel]", JSON.stringify(filterModel, null, 2));
    }
  }, [filterModel]);

  return (
    <DataGrid
      rows={rows}
      columns={columns}
      rowCount={rowCount}
      loading={loading}
      autoHeight={autoHeight}
      disableRowSelectionOnClick
      paginationMode="server"
      filterMode="server"
      paginationModel={paginationModel}
      onPaginationModelChange={setPaginationModel}
      filterModel={filterModel}
      onFilterModelChange={handleFilterModelChange}
      pageSizeOptions={pageSizeOptions}
      initialState={{
        density: "compact",
        pagination: { paginationModel: { pageSize: initialPageSize } },
      }}
      slots={{
        toolbar: CustomToolbar,
        loadingOverlay: LinearProgress,
      }}
      columnHeaderHeight={85}
      {...props}
    />
  );
}
