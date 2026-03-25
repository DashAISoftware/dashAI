import { useCallback, useEffect, useMemo, useState } from "react";
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

  const CLIENT_SIDE_THRESHOLD = 2000;

  const [data, setData] = useState([]);
  const [rowCount, setRowCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [columnOrder, setColumnOrder] = useState([]);
  const [density, setDensity] = useState("compact");
  const [allFilteredData, setAllFilteredData] = useState(null); // null = server-side mode

  const storageKey = datasetId
    ? `mrt-state-${datasetId}`
    : datasetPath
      ? `mrt-state-${datasetPath}`
      : null;

  const loadFromStorage = (storage, key) => {
    if (!key) return null;
    try {
      const saved = storage.getItem(key);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  };

  const prefsKey = storageKey ? `${storageKey}-prefs` : null;
  const sessionKey = storageKey ? `${storageKey}-session` : null;

  const [pagination, setPagination] = useState(() => {
    const prefs = loadFromStorage(localStorage, prefsKey);
    return { pageIndex: 0, pageSize: prefs?.pageSize ?? initialPageSize };
  });
  const [columnFilters, setColumnFilters] = useState(() => {
    const session = loadFromStorage(sessionStorage, sessionKey);
    return (session?.columnFilters ?? []).filter(
      (f) =>
        f.id !== undefined &&
        !Array.isArray(f.value) &&
        f.value !== undefined &&
        f.value !== "",
    );
  });
  const [sorting, setSorting] = useState(() => {
    const session = loadFromStorage(sessionStorage, sessionKey);
    return session?.sorting ?? [];
  });
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

  const [columnFilterFns, setColumnFilterFns] = useState(() => {
    const session = loadFromStorage(sessionStorage, sessionKey);
    return session?.columnFilterFns ?? getDefaultFilterFns();
  });
  const [showColumnFilters, setShowColumnFilters] = useState(() => {
    const prefs = loadFromStorage(localStorage, prefsKey);
    return prefs?.showColumnFilters ?? false;
  });

  useEffect(() => {
    setData([]);
    setRowCount(0);
    setAllFilteredData(null);
    setIsLoading(true);

    const prefs = loadFromStorage(localStorage, prefsKey);
    const session = loadFromStorage(sessionStorage, sessionKey);
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
    setShowColumnFilters(prefs?.showColumnFilters ?? false);
    setDensity(prefs?.density ?? "compact");
    setPagination({
      pageIndex: 0,
      pageSize: prefs?.pageSize ?? initialPageSize,
    });
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps

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
  }, [columnTypes]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!prefsKey) return;
    try {
      localStorage.setItem(
        prefsKey,
        JSON.stringify({
          pageSize: pagination.pageSize,
          density,
          showColumnFilters,
        }),
      );
    } catch {}
  }, [prefsKey, pagination.pageSize, density, showColumnFilters]);

  useEffect(() => {
    if (!sessionKey) return;
    try {
      sessionStorage.setItem(
        sessionKey,
        JSON.stringify({
          columnFilters,
          columnFilterFns,
          sorting,
        }),
      );
    } catch {}
  }, [sessionKey, columnFilters, columnFilterFns, sorting]);

  const buildFilterModel = useCallback(
    () => ({
      items: columnFilters
        .filter((f) => {
          const fn = columnFilterFns[f.id];
          if (fn === "empty" || fn === "notEmpty") return true;
          if (fn !== "between" && Array.isArray(f.value)) return false;
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

  // Fetch data when filters or sorting change — decide server-side vs client-side
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      try {
        const muiFormattedFilters = buildFilterModel();

        // First, fetch page 0 to discover total row count
        const response = await fetchPage(
          0,
          pagination.pageSize,
          muiFormattedFilters,
          sorting,
        );

        const total = response?.total ?? 0;
        const firstPageRows = response?.rows ?? [];

        if (total > 0 && total <= CLIENT_SIDE_THRESHOLD) {
          // Fetch ALL filtered rows at once for client-side pagination
          let allRows = firstPageRows;
          if (total > pagination.pageSize) {
            const fullResponse = await fetchPage(
              0,
              total,
              muiFormattedFilters,
              sorting,
            );
            allRows = fullResponse?.rows ?? firstPageRows;
          }
          setAllFilteredData(allRows);
          setRowCount(total);
          // Slice locally for the current page
          const start = pagination.pageIndex * pagination.pageSize;
          setData(allRows.slice(start, start + pagination.pageSize));
          if (allRows.length > 0) {
            setColumnOrder(Object.keys(allRows[0]).filter((k) => k !== "id"));
          }
        } else {
          // Large dataset — stay in server-side mode
          setAllFilteredData(null);
          setData(firstPageRows);
          setRowCount(total);
          if (firstPageRows.length > 0) {
            setColumnOrder(
              Object.keys(firstPageRows[0]).filter((k) => k !== "id"),
            );
          }
        }
      } catch (error) {
        console.error("Error loading data:", error);
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [columnFilters, sorting, pagination.pageSize, ...deps]); // eslint-disable-line react-hooks/exhaustive-deps

  // Handle page changes — use local data if available, otherwise fetch from server
  useEffect(() => {
    if (allFilteredData) {
      const start = pagination.pageIndex * pagination.pageSize;
      setData(allFilteredData.slice(start, start + pagination.pageSize));
      return;
    }

    // Server-side pagination: fetch the requested page
    const loadPage = async () => {
      setIsLoading(true);
      try {
        const muiFormattedFilters = buildFilterModel();
        const response = await fetchPage(
          pagination.pageIndex,
          pagination.pageSize,
          muiFormattedFilters,
          sorting,
        );
        const rows = response?.rows ?? [];
        setData(rows);
        setRowCount(response?.total ?? 0);
      } catch (error) {
        console.error("Error loading page:", error);
      } finally {
        setIsLoading(false);
      }
    };

    loadPage();
  }, [pagination.pageIndex]); // eslint-disable-line react-hooks/exhaustive-deps

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
