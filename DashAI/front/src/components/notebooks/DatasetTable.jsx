// src/components/common/ServerDataGrid.jsx
import { useEffect, useMemo, useState } from "react";
import { DataGrid, GridToolbar } from "@mui/x-data-grid";
import { LinearProgress } from "@mui/material";

/**
 * Props:
 * - fetchPage: async (page, pageSize) => { rows: Array<object>, total: number }
 * - initialPageSize?: number (default 5)
 * - columns?: GridColDef[] (optional)
 * - deps?: any[] (optional)
 * - autoHeight?: boolean (default true)
 * - pageSizeOptions?: number[] (default [5, 10, 25])
 */
export default function DatasetTable({
  fetchPage,
  initialPageSize = 5,
  columns: columnsProp,
  deps = [],
  autoHeight = true,
  density = "standard",
  pageSizeOptions = [5, 10, 25],
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
        toolbar: GridToolbar,
        loadingOverlay: LinearProgress,
      }}
    />
  );
}
