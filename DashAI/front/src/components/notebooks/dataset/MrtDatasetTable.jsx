import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  MaterialReactTable,
  useMaterialReactTable,
} from "material-react-table";
import { MRT_Localization_ES } from "material-react-table/locales/es";
import { MRT_Localization_EN } from "material-react-table/locales/en";
import { Box, Button, Tooltip, Typography } from "@mui/material";
import FileDownloadIcon from "@mui/icons-material/FileDownload";
import { useTheme } from "@mui/material/styles";
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
  const { t, i18n } = useTranslation(["common"]);
  const theme = useTheme();
  const localization = i18n.language.startsWith("es")
    ? MRT_Localization_ES
    : MRT_Localization_EN;

  // Only load all data client-side if:
  // 1. Filters/sorting are active AND
  // 2. Dataset is small enough (<=2000 rows)
  // Otherwise, use server-side filtering for performance
  const CLIENT_SIDE_THRESHOLD = 2000;
  const initialized = useRef(false);
  const isLoadingFullDataRef = useRef(false);

  const [data, setData] = useState([]);
  const [rowCount, setRowCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [columnOrder, setColumnOrder] = useState([]);
  const [density, setDensity] = useState("compact");
  const [allFilteredData, setAllFilteredData] = useState(null);
  const [totalRowCount, setTotalRowCount] = useState(0); // Track actual total without filters

  const sessionKey = datasetId
    ? `mrt-filters-${datasetId}`
    : datasetPath
      ? `mrt-filters-${datasetPath}`
      : null;

  const loadSessionFilters = () => {
    if (!sessionKey) return null;
    try {
      const saved = sessionStorage.getItem(sessionKey);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  };

  const [pagination, setPagination] = useState({
    pageIndex: 0,
    pageSize: initialPageSize,
  });
  const [columnFilters, setColumnFilters] = useState([]);
  const [sorting, setSorting] = useState([]);

  const getDefaultFilterFns = () => {
    const defaults = {};
    Object.entries(columnTypes).forEach(([key, typeRaw]) => {
      const type =
        typeof typeRaw === "string" ? typeRaw : (typeRaw?.type ?? "");
      defaults[key] = ["Integer", "Float"].includes(type)
        ? "between"
        : "contains";
    });
    return defaults;
  };

  const [columnFilterFns, setColumnFilterFns] = useState(getDefaultFilterFns);
  const [showColumnFilters, setShowColumnFilters] = useState(false);

  useEffect(() => {
    initialized.current = false;
    isLoadingFullDataRef.current = false;

    setData([]);
    setRowCount(0);
    setTotalRowCount(0);
    setAllFilteredData(null);
    setIsLoading(true);
    setShowColumnFilters(false);
    setDensity("compact");

    const session = loadSessionFilters();
    const cleanFilters = (session?.columnFilters ?? []).filter(
      (f) =>
        f.id !== undefined &&
        !Array.isArray(f.value) &&
        f.value !== undefined &&
        f.value !== "",
    );
    setColumnFilters(cleanFilters);
    setSorting(session?.sorting ?? []);
    setColumnFilterFns(session?.columnFilterFns ?? getDefaultFilterFns());
    setPagination({ pageIndex: 0, pageSize: initialPageSize });

    initialized.current = true;
  }, deps);

  useEffect(() => {
    setColumnFilterFns((prev) => {
      const defaults = getDefaultFilterFns();
      const merged = { ...defaults };
      for (const key of Object.keys(prev)) {
        if (key in merged && prev[key] !== undefined) {
          merged[key] = prev[key];
        }
      }
      return merged;
    });
  }, [columnTypes]);

  useEffect(() => {
    if (!sessionKey) return;
    try {
      sessionStorage.setItem(
        sessionKey,
        JSON.stringify({ columnFilters, columnFilterFns, sorting }),
      );
    } catch {}
  }, [sessionKey, columnFilters, columnFilterFns, sorting]);

  const buildFilterModel = useCallback(
    () => ({
      items: columnFilters
        .filter((f) => {
          const fn = columnFilterFns[f.id];
          if (fn === "empty" || fn === "notEmpty") return true;
          // Skip between filters where both values are null/empty
          if (
            (fn === "between" || Array.isArray(f.value)) &&
            Array.isArray(f.value)
          ) {
            return f.value.some(
              (v) => v !== null && v !== undefined && v !== "",
            );
          }
          if (Array.isArray(f.value)) return false;
          return f.value !== undefined && f.value !== "";
        })
        .map((f) => {
          const fn = columnFilterFns[f.id];
          if (fn === "empty")
            return { field: f.id, value: null, operator: "isEmpty" };
          if (fn === "notEmpty")
            return { field: f.id, value: null, operator: "isNotEmpty" };
          const colTypeRaw = columnTypes[f.id];
          const colType =
            typeof colTypeRaw === "string"
              ? colTypeRaw
              : (colTypeRaw?.type ?? "");
          const operator =
            fn ??
            (["Integer", "Float"].includes(colType) ? "between" : "contains");
          const value =
            operator === "between" && typeof f.value === "string"
              ? f.value.split(",").map((v) => v.trim() || null)
              : f.value;
          return { field: f.id, value, operator };
        }),
    }),
    [columnFilters, columnFilterFns, columnTypes],
  );

  // Clear cached data when filters/sorting change
  // Reset lazy-load flag to allow re-fetching full data if needed
  useEffect(() => {
    if (allFilteredData) {
      setAllFilteredData(null);
      isLoadingFullDataRef.current = false;
    }
  }, [columnFilters, sorting]);

  // Main data loading effect with lazy-load strategy:
  // 1st load: only fetch current page (fast, like develop)
  // If filters active and dataset small: lazy-load all data for client-side filtering
  useEffect(() => {
    if (!initialized.current) return;

    // If we have cached filtered data, use it for pagination
    if (allFilteredData) {
      const start = pagination.pageIndex * pagination.pageSize;
      setData(allFilteredData.slice(start, start + pagination.pageSize));
      setIsLoading(false);
      return;
    }

    let cancelled = false;

    const loadData = async () => {
      setIsLoading(true);
      try {
        const muiFormattedFilters = buildFilterModel();
        const hasActiveFilters = columnFilters.length > 0;
        const hasSorting = sorting.length > 0;

        // FAST PATH: First load OR server-side filtering
        // Only fetch the page we need
        const response = await fetchPage(
          pagination.pageIndex,
          pagination.pageSize,
          muiFormattedFilters,
          sorting,
        );
        if (cancelled) return;

        const total = response?.total ?? 0;
        const rows = response?.rows ?? [];

        // Track total for lazy-load decision
        setTotalRowCount(total);
        setData(rows);
        setRowCount(total);

        if (rows.length > 0) {
          setColumnOrder(Object.keys(rows[0]).filter((k) => k !== "id"));
        }

        // LAZY-LOAD: Only fetch all data if:
        // 1. User has active filters AND
        // 2. Dataset is small enough for client-side filtering AND
        // 3. We haven't already loaded it
        if (
          (hasActiveFilters || hasSorting) &&
          total > 0 &&
          total <= CLIENT_SIDE_THRESHOLD &&
          total > pagination.pageSize &&
          !isLoadingFullDataRef.current
        ) {
          isLoadingFullDataRef.current = true;
          setIsLoading(true);

          const fullResponse = await fetchPage(
            0,
            total,
            muiFormattedFilters,
            sorting,
          );
          if (cancelled) return;

          const allRows = fullResponse?.rows ?? rows;
          setAllFilteredData(allRows);
          setRowCount(total);
          const start = pagination.pageIndex * pagination.pageSize;
          setData(allRows.slice(start, start + pagination.pageSize));
        }
      } catch (error) {
        if (!cancelled) {
          console.error("Error loading data:", error);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    loadData();

    return () => {
      cancelled = true;
    };
  }, [pagination.pageIndex, pagination.pageSize, columnFilters, sorting]);

  const handleColumnRename = useCallback(
    async (oldName, newName) => {
      if (!datasetId) {
        throw new Error("Dataset ID is required for renaming columns");
      }
      const result = await renameDatasetColumn(datasetId, oldName, newName);
      onEditColumn && (await onEditColumn(result));

      setColumnOrder((prev) =>
        prev.map((col) => (col === oldName ? newName : col)),
      );

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

    const getColType = (key) => {
      const val = columnTypes[key];
      if (!val) return null;
      return typeof val === "string" ? val : (val.type ?? null);
    };

    return columnKeys.map((key) => {
      const colTypeRaw = columnTypes[key];
      const colType =
        typeof colTypeRaw === "string" ? colTypeRaw : (colTypeRaw?.type ?? "");
      const filterVariant = "text";
      return {
        accessorKey: key,
        header: key,
        filterVariant,
        filterFn: ["Integer", "Float"].includes(colType)
          ? "between"
          : "contains",
        columnFilterModeOptions: ["Integer", "Float"].includes(colType)
          ? [
              "equals",
              "between",
              "lessThan",
              "lessThanOrEqualTo",
              "greaterThan",
              "greaterThanOrEqualTo",
              "empty",
              "notEmpty",
            ]
          : [
              "contains",
              "startsWith",
              "endsWith",
              "equals",
              "empty",
              "notEmpty",
            ],
        Header: () =>
          editableColumns && datasetId ? (
            <div onDoubleClick={(e) => e.stopPropagation()}>
              <EditableColumnHeader
                columnName={key}
                columnType={getColType(key)}
                onRename={handleColumnRename}
              />
            </div>
          ) : (
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: "bold" }}>
                {key}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {getColType(key) || t("common:unknown")}
              </Typography>
            </Box>
          ),
      };
    });
  }, [data, columnTypes, editableColumns, datasetId, handleColumnRename, t]);

  const handleExportFilteredRows = useCallback(async () => {
    if (rowCount === 0) return;
    try {
      let rows;
      if (allFilteredData) {
        rows = allFilteredData;
      } else {
        const muiFormattedFilters = buildFilterModel();
        const response = await fetchPage(
          0,
          rowCount,
          muiFormattedFilters,
          sorting,
        );
        rows = response?.rows ?? [];
      }
      if (rows.length === 0) return;

      const headers = Object.keys(rows[0]).filter((k) => k !== "id");
      const csvRows = [headers.join(",")];
      for (const row of rows) {
        csvRows.push(
          headers
            .map((h) => {
              const val = row[h] ?? "";
              const str = String(val);
              return str.includes(",") ||
                str.includes('"') ||
                str.includes("\n")
                ? `"${str.replace(/"/g, '""')}"`
                : str;
            })
            .join(","),
        );
      }
      const blob = new Blob([csvRows.join("\n")], {
        type: "text/csv;charset=utf-8;",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "dataset_filtered.csv";
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Error exporting filtered data:", error);
    }
  }, [rowCount, allFilteredData, buildFilterModel, sorting, fetchPage]);

  const table = useMaterialReactTable({
    columns,
    data,
    rowCount,
    localization,
    mrtTheme: { baseBackgroundColor: theme.palette.ui.panelDark },
    muiTablePaperProps: { elevation: 0 },
    enablePagination: true,
    manualPagination: true,
    manualFiltering: true,
    manualSorting: true,
    enableFilters: true,
    enableColumnFilterModes: true,
    onPaginationChange: setPagination,
    onColumnFiltersChange: setColumnFilters,
    onColumnFilterFnsChange: setColumnFilterFns,
    onSortingChange: setSorting,
    onDensityChange: setDensity,
    onShowColumnFiltersChange: setShowColumnFilters,
    renderTopToolbarCustomActions: () => (
      <Tooltip
        title={
          columnFilters.length > 0
            ? t("common:exportFilteredTooltip")
            : t("common:exportAllTooltip")
        }
        arrow
      >
        <span>
          <Button
            onClick={handleExportFilteredRows}
            disabled={rowCount === 0}
            startIcon={<FileDownloadIcon />}
            variant="text"
            size="small"
          >
            {columnFilters.length > 0
              ? t("common:exportFiltered")
              : t("common:export")}
          </Button>
        </span>
      </Tooltip>
    ),
    state: {
      pagination,
      columnFilters,
      columnFilterFns,
      sorting,
      columnOrder,
      showColumnFilters,
      density,
      isLoading,
    },
  });

  return (
    <Box sx={{ width: "100%" }}>
      <MaterialReactTable table={table} />
    </Box>
  );
}
