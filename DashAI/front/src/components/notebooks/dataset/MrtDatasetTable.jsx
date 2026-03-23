import { useCallback, useEffect, useMemo, useState } from "react";
import {
  MaterialReactTable,
  useMaterialReactTable,
} from "material-react-table";
import { Box, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { renameDatasetColumn } from "../../../api/datasets";
import EditableColumnHeader from "./EditableColumnHeader";

export default function MrtDatasetTable({
  fetchPage,
  initialPageSize = 5,
  deps = [],
  datasetPath,
  datasetId,
  columnTypes = {},
  editableColumns = false,
  onEditColumn = null,
}) {
  const { t } = useTranslation(["common"]);

  const [data, setData] = useState([]);
  const [rowCount, setRowCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [columnOrder, setColumnOrder] = useState([]);

  const [pagination, setPagination] = useState({
    pageIndex: 0,
    pageSize: initialPageSize,
  });
  const [columnFilters, setColumnFilters] = useState([]);
  const [sorting, setSorting] = useState([]);

  // Resetear filtros, sorting y paginación al cambiar de dataset
  useEffect(() => {
    setColumnFilters([]);
    setSorting([]);
    setPagination({ pageIndex: 0, pageSize: initialPageSize });
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps

  // Cargar datos (server-side)
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      try {
        const muiFormattedFilters = {
          items: columnFilters.map((f) => ({
            field: f.id,
            value: f.value,
            operator: "contains",
          })),
        };

        const response = await fetchPage(
          pagination.pageIndex,
          pagination.pageSize,
          muiFormattedFilters,
          sorting,
        );

        const rows = response?.rows ?? [];
        setData(rows);
        setRowCount(response?.total ?? 0);
        if (rows.length > 0) {
          setColumnOrder(Object.keys(rows[0]).filter((k) => k !== "id"));
        }
      } catch (error) {
        console.error("Error loading data:", error);
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [
    pagination.pageIndex,
    pagination.pageSize,
    columnFilters,
    sorting,
    ...deps,
  ]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleColumnRename = useCallback(
    async (oldName, newName) => {
      if (!datasetId) {
        throw new Error("Dataset ID is required for renaming columns");
      }
      const result = await renameDatasetColumn(datasetId, oldName, newName);
      onEditColumn && (await onEditColumn(result));

      // Actualizar el orden de columnas preservando la posición del rename
      setColumnOrder((prev) =>
        prev.map((col) => (col === oldName ? newName : col)),
      );

      // Refrescar datos para reflejar el nuevo nombre de columna
      const muiFormattedFilters = {
        items: columnFilters.map((f) => ({
          field: f.id,
          value: f.value,
          operator: "contains",
        })),
      };
      const response = await fetchPage(
        pagination.pageIndex,
        pagination.pageSize,
        muiFormattedFilters,
      );
      const rows = response?.rows ?? [];
      setData(rows);
      setRowCount(response?.total ?? 0);

      return result;
    },
    [datasetId, onEditColumn, columnFilters, pagination, fetchPage],
  );

  const columns = useMemo(() => {
    let columnKeys = [];

    if (data.length > 0) {
      columnKeys = Object.keys(data[0]).filter((key) => key !== "id");
    } else if (Object.keys(columnTypes).length > 0) {
      columnKeys = Object.keys(columnTypes);
    } else {
      return [];
    }

    return columnKeys.map((key) => ({
      accessorKey: key,
      header: key,
      Header: () =>
        editableColumns && datasetId ? (
          // onDoubleClick stopPropagation: evita que MRT intercepte el doble-click
          // (que activa el rename), pero el single-click sigue llegando para ordenar
          <div onDoubleClick={(e) => e.stopPropagation()}>
            <EditableColumnHeader
              columnName={key}
              columnType={columnTypes[key]?.type}
              onRename={handleColumnRename}
            />
          </div>
        ) : (
          <Box>
            <Typography variant="subtitle2" sx={{ fontWeight: "bold" }}>
              {key}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {columnTypes[key]?.type || t("common:unknown")}
            </Typography>
          </Box>
        ),
    }));
  }, [data, columnTypes, editableColumns, datasetId, handleColumnRename, t]);

  const table = useMaterialReactTable({
    columns,
    data,
    rowCount,
    enablePagination: true,
    manualPagination: true,
    manualFiltering: true,
    manualSorting: true,
    enableFilters: true,
    onPaginationChange: setPagination,
    onColumnFiltersChange: setColumnFilters,
    onSortingChange: setSorting,
    state: {
      pagination,
      columnFilters,
      sorting,
      columnOrder,
      isLoading,
    },
  });

  return (
    <Box sx={{ width: "100%" }}>
      <MaterialReactTable table={table} />
    </Box>
  );
}
