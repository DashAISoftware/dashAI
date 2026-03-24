import { useCallback, useEffect, useMemo, useState } from "react";
import {
  MaterialReactTable,
  useMaterialReactTable,
} from "material-react-table";
import { MRT_Localization_ES } from "material-react-table/locales/es";
import { MRT_Localization_EN } from "material-react-table/locales/en";
import { Box, Typography } from "@mui/material";
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

  const [data, setData] = useState([]);
  const [rowCount, setRowCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [columnOrder, setColumnOrder] = useState([]);
  const [density, setDensity] = useState("compact");

  const storageKey = datasetId
    ? `mrt-state-${datasetId}`
    : datasetPath
      ? `mrt-state-${datasetPath}`
      : null;

  const loadPersistedState = (key) => {
    if (!key) return null;
    try {
      const saved = localStorage.getItem(key);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  };

  const [pagination, setPagination] = useState(() => {
    const saved = loadPersistedState(storageKey);
    return { pageIndex: 0, pageSize: saved?.pageSize ?? initialPageSize };
  });
  const [columnFilters, setColumnFilters] = useState(() => {
    const saved = loadPersistedState(storageKey);
    return (saved?.columnFilters ?? []).filter(
      (f) =>
        f.id !== undefined &&
        !Array.isArray(f.value) &&
        f.value !== undefined &&
        f.value !== "",
    );
  });
  const [sorting, setSorting] = useState(() => {
    const saved = loadPersistedState(storageKey);
    return saved?.sorting ?? [];
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
    const saved = loadPersistedState(storageKey);
    return saved?.columnFilterFns ?? getDefaultFilterFns();
  });

  // Al cambiar de dataset, cargar el estado guardado (o defaults)
  useEffect(() => {
    const saved = loadPersistedState(storageKey);
    const cleanFilters = (saved?.columnFilters ?? []).filter(
      (f) =>
        f.id !== undefined &&
        !Array.isArray(f.value) &&
        f.value !== undefined &&
        f.value !== "",
    );
    setColumnFilters(cleanFilters);
    setSorting(saved?.sorting ?? []);
    setColumnFilterFns(saved?.columnFilterFns ?? getDefaultFilterFns());
    setDensity(saved?.density ?? "compact");
    setPagination({
      pageIndex: 0,
      pageSize: saved?.pageSize ?? initialPageSize,
    });
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps

  // Guardar estado en localStorage cuando cambia
  useEffect(() => {
    if (!storageKey) return;
    try {
      localStorage.setItem(
        storageKey,
        JSON.stringify({
          pageSize: pagination.pageSize,
          columnFilters,
          columnFilterFns,
          sorting,
          density,
        }),
      );
    } catch {}
  }, [
    storageKey,
    pagination.pageSize,
    columnFilters,
    columnFilterFns,
    sorting,
    density,
  ]);

  // Cargar datos (server-side)
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      try {
        const muiFormattedFilters = {
          items: columnFilters
            .filter((f) => {
              const fn = columnFilterFns[f.id];
              if (fn === "empty" || fn === "notEmpty") return true;
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
                (["Integer", "Float"].includes(colType)
                  ? "between"
                  : "contains");
              // between espera [min, max]: parsear "min,max" del input de texto
              const value =
                operator === "between" && typeof f.value === "string"
                  ? f.value.split(",").map((v) => v.trim() || null)
                  : f.value;
              return { field: f.id, value, operator };
            }),
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

    // columnTypes puede venir como { col: "Integer" } o { col: { type: "Integer" } }
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
            // onDoubleClick stopPropagation: evita que MRT intercepte el doble-click
            // (que activa el rename), pero el single-click sigue llegando para ordenar
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
    state: {
      pagination,
      columnFilters,
      columnFilterFns,
      sorting,
      columnOrder,
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
