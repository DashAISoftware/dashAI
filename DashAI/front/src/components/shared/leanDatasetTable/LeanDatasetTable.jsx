import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import { Box, Checkbox, TablePagination, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";

import { exportDatasetCsvByPath } from "../../../api/datasets";
import LeanCell from "./LeanCell";
import LeanColumnsMenu from "./LeanColumnsMenu";
import LeanFilterCell from "./LeanFilterCell";
import LeanHeaderCell from "./LeanHeaderCell";
import LeanToolbar from "./LeanToolbar";
import { defaultOpForType, toBackendOperator } from "./operators";

import "./leanDatasetTable.css";

/**
 * Lightweight dataset preview table. Renders a native ``<table>`` with a
 * sticky header and server-side pagination via ``fetchPage``. Supports
 * column visibility, an optional per-column filter row, and an encoder
 * selector on Categorical columns.
 */
function LeanDatasetTable({
  fetchPage,
  initialPageSize = 10,
  deps = [],
  columnTypes = {},
  datasetId,
  datasetPath,
  datasetName = "dataset",
  onColumnChanged,
  enableFilters = true,
  enableSearch = true,
  enableRowsPerPage = true,
  enableColumnVisibility = true,
  showExportButton = true,
  onRowClick = null,
  selectedRowIndex = null,
  enableRowSelection = false,
  selectedRowIndices = null,
  onRowSelectionChange = null,
}) {
  const theme = useTheme();
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["datasets"]);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(initialPageSize);
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [isExporting, setIsExporting] = useState(false);

  const [hiddenColumns, setHiddenColumns] = useState(() => new Set());
  const [showFilters, setShowFilters] = useState(false);
  const [filterValues, setFilterValues] = useState({});
  const [filterOperators, setFilterOperators] = useState({});
  const [debouncedFilterValues, setDebouncedFilterValues] = useState({});
  const [debouncedFilterOperators, setDebouncedFilterOperators] = useState({});
  const filterDebounceRef = useRef(null);
  const [searchValue, setSearchValue] = useState("");
  // Debounced version drives the cell highlighting work. Re-rendering every
  // cell on each keystroke is the dominant cost on wide datasets.
  const [debouncedSearchValue, setDebouncedSearchValue] = useState("");
  const searchDebounceRef = useRef(null);

  const [columnsAnchor, setColumnsAnchor] = useState(null);
  const [editingColumn, setEditingColumn] = useState(null);
  // Single-column sort: ``{ id: columnName, desc: boolean }`` or null.
  const [sort, setSort] = useState(null);
  // Bumped after operations that mutate the dataset (e.g. column rename) to
  // force the next fetch effect to re-run and pull rows with the new schema.
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    setPage(0);
    setPageSize(initialPageSize);
    setHiddenColumns(new Set());
    setShowFilters(false);
    setFilterValues({});
    setFilterOperators({});
    setDebouncedFilterValues({});
    setDebouncedFilterOperators({});
    setSearchValue("");
    setDebouncedSearchValue("");
    setEditingColumn(null);
    setSort(null);
  }, deps);

  // Debounce search -> debouncedSearchValue (drives cell highlighting).
  useEffect(() => {
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    searchDebounceRef.current = setTimeout(() => {
      setDebouncedSearchValue(searchValue);
    }, 200);
    return () => {
      if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    };
  }, [searchValue]);

  // Debounce filter input -> debounced state, which drives the fetch.
  useEffect(() => {
    if (filterDebounceRef.current) clearTimeout(filterDebounceRef.current);
    filterDebounceRef.current = setTimeout(() => {
      setDebouncedFilterValues(filterValues);
      setDebouncedFilterOperators(filterOperators);
      setPage(0);
    }, 250);
    return () => {
      if (filterDebounceRef.current) clearTimeout(filterDebounceRef.current);
    };
  }, [filterValues, filterOperators]);

  const getColType = (key) => {
    const v = columnTypes[key];
    if (!v) return "";
    return typeof v === "string" ? v : (v?.type ?? "");
  };

  const filterModel = useMemo(() => {
    const items = [];
    const keys = new Set([
      ...Object.keys(debouncedFilterOperators),
      ...Object.keys(debouncedFilterValues),
    ]);
    for (const field of keys) {
      const type = getColType(field);
      const op = debouncedFilterOperators[field] ?? defaultOpForType(type);
      const val = debouncedFilterValues[field];

      if (op === "empty" || op === "notEmpty") {
        items.push({ field, operator: toBackendOperator(op), value: null });
        continue;
      }
      if (op === "between") {
        const range = Array.isArray(val) ? val : null;
        if (!range) continue;
        const min = range[0];
        const max = range[1];
        const hasMin = min != null && String(min).trim() !== "";
        const hasMax = max != null && String(max).trim() !== "";
        if (!hasMin && !hasMax) continue;
        items.push({ field, operator: "between", value: [min, max] });
        continue;
      }
      if (val == null || String(val).trim() === "") continue;
      items.push({ field, operator: toBackendOperator(op), value: val });
    }
    return items.length > 0 ? { items } : null;
  }, [debouncedFilterValues, debouncedFilterOperators, columnTypes]);

  const sortModel = useMemo(() => (sort ? [sort] : null), [sort]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchPage(page, pageSize, filterModel, sortModel)
      .then(({ rows: r, total: t }) => {
        if (cancelled) return;
        setRows(r ?? []);
        setTotal(t ?? 0);
      })
      .catch(() => {
        if (cancelled) return;
        setRows([]);
        setTotal(0);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [page, pageSize, filterModel, sortModel, refreshKey, ...deps]);

  const allColumnKeys =
    rows.length > 0
      ? Object.keys(rows[0]).filter((k) => k !== "id")
      : Object.keys(columnTypes);

  const visibleColumnKeys = useMemo(
    () => allColumnKeys.filter((k) => !hiddenColumns.has(k)),
    [allColumnKeys, hiddenColumns],
  );

  const highlightQuery = debouncedSearchValue.trim();

  const toggleColumn = (key) => {
    setHiddenColumns((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const handleFilterValueChange = (key, value) => {
    setFilterValues((prev) => ({ ...prev, [key]: value }));
  };

  const handleFilterOperatorChange = (key, op) => {
    setFilterOperators((prev) => ({ ...prev, [key]: op }));
    // Reset value when the operator's value shape changes so stale data
    // doesn't carry over.
    setFilterValues((prev) => {
      const prevVal = prev[key];
      const next = { ...prev };
      if (op === "empty" || op === "notEmpty") {
        delete next[key];
      } else if (op === "between" && !Array.isArray(prevVal)) {
        next[key] = ["", ""];
      } else if (op !== "between" && Array.isArray(prevVal)) {
        next[key] = "";
      }
      return next;
    });
  };

  const showAllColumns = useCallback(() => setHiddenColumns(new Set()), []);
  const hideAllColumns = useCallback(
    () => setHiddenColumns(new Set(allColumnKeys)),
    [allColumnKeys],
  );

  // Stable callbacks for the memoized toolbar - without these, the toolbar
  // re-renders on every page / row change because the inline arrows would
  // change reference each render.
  const handleOpenColumnsMenu = useCallback(
    (e) => setColumnsAnchor(e.currentTarget),
    [],
  );
  const handleToggleFilters = useCallback(() => setShowFilters((v) => !v), []);
  const handleSearchChange = useCallback(
    (e) => setSearchValue(e.target.value),
    [],
  );
  const handleClearSearch = useCallback(() => {
    setSearchValue("");
    setDebouncedSearchValue("");
  }, []);

  // Sort cycle: not sorted -> asc -> desc -> not sorted.
  const handleSortClick = useCallback((key) => {
    setSort((prev) => {
      if (!prev || prev.id !== key) return { id: key, desc: false };
      if (!prev.desc) return { id: key, desc: true };
      return null;
    });
    setPage(0);
  }, []);

  const handleExport = useCallback(async () => {
    if (!datasetPath) return;
    setIsExporting(true);
    try {
      const blob = await exportDatasetCsvByPath(
        datasetPath,
        filterModel ?? undefined,
        sortModel ?? undefined,
      );
      const isZip =
        blob.type === "application/zip" ||
        blob.type === "application/octet-stream";
      const ext = isZip ? "zip" : "csv";
      const filename = filterModel
        ? `${datasetName}_filtered.${ext}`
        : `${datasetName}.${ext}`;
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      enqueueSnackbar(t("datasets:table.failedToExport", { datasetName }), {
        variant: "error",
      });
    } finally {
      setIsExporting(false);
    }
  }, [datasetPath, datasetName, filterModel, sortModel, enqueueSnackbar]);

  const handleCommitRename = useCallback(() => {
    setEditingColumn(null);
    setRefreshKey((k) => k + 1);
    if (onColumnChanged) onColumnChanged();
  }, [onColumnChanged]);

  const handleCancelRename = useCallback(() => setEditingColumn(null), []);

  // Absolute (cross-page) index of each rendered row. This is the row's real
  // position in the dataset only while sort/filter are off, so callers that
  // rely on the selection for indexing should keep those disabled.
  const pageGlobalIndices = useMemo(
    () => rows.map((_, i) => page * pageSize + i),
    [rows, page, pageSize],
  );

  const allPageSelected =
    enableRowSelection &&
    pageGlobalIndices.length > 0 &&
    selectedRowIndices != null &&
    pageGlobalIndices.every((idx) => selectedRowIndices.has(idx));
  const somePageSelected =
    enableRowSelection &&
    selectedRowIndices != null &&
    pageGlobalIndices.some((idx) => selectedRowIndices.has(idx));

  const toggleRowSelected = useCallback(
    (globalIndex) => {
      if (!onRowSelectionChange) return;
      const next = new Set(selectedRowIndices ?? []);
      if (next.has(globalIndex)) next.delete(globalIndex);
      else next.add(globalIndex);
      onRowSelectionChange(next);
    },
    [onRowSelectionChange, selectedRowIndices],
  );

  const toggleAllOnPage = useCallback(() => {
    if (!onRowSelectionChange) return;
    const next = new Set(selectedRowIndices ?? []);
    if (allPageSelected) {
      pageGlobalIndices.forEach((idx) => next.delete(idx));
    } else {
      pageGlobalIndices.forEach((idx) => next.add(idx));
    }
    onRowSelectionChange(next);
  }, [
    onRowSelectionChange,
    selectedRowIndices,
    allPageSelected,
    pageGlobalIndices,
  ]);

  return (
    <Box
      className="lean-root"
      sx={{
        "--lean-header-bg": theme.palette.ui.panelDark,
        "--lean-header-fg": theme.palette.text.primary,
        "--lean-body-bg": theme.palette.ui.panelDark,
        "--lean-row-hover": theme.palette.action.hover,
      }}
    >
      <LeanToolbar
        hiddenColumnsCount={hiddenColumns.size}
        loading={loading}
        showFilters={showFilters}
        searchValue={searchValue}
        enableFilters={enableFilters}
        enableSearch={enableSearch}
        enableColumnVisibility={enableColumnVisibility}
        showExportButton={showExportButton && Boolean(datasetPath)}
        isExporting={isExporting}
        hasActiveFilters={Boolean(filterModel)}
        onOpenColumnsMenu={handleOpenColumnsMenu}
        onToggleFilters={handleToggleFilters}
        onSearchChange={handleSearchChange}
        onClearSearch={handleClearSearch}
        onExport={handleExport}
      />

      <LeanColumnsMenu
        anchor={columnsAnchor}
        allColumnKeys={allColumnKeys}
        hiddenColumns={hiddenColumns}
        onClose={() => setColumnsAnchor(null)}
        onToggleColumn={toggleColumn}
        onShowAll={showAllColumns}
        onHideAll={hideAllColumns}
      />

      <div className="lean-scroll">
        <table className="lean-table">
          <thead>
            <tr>
              {enableRowSelection && (
                <th className="lean-th lean-th--select">
                  <Checkbox
                    size="small"
                    checked={allPageSelected}
                    indeterminate={!allPageSelected && somePageSelected}
                    onChange={toggleAllOnPage}
                    disabled={pageGlobalIndices.length === 0}
                  />
                </th>
              )}
              {visibleColumnKeys.map((key) => {
                const type = getColType(key);
                const colSpec = columnTypes[key];
                const encoder =
                  type === "Categorical" &&
                  colSpec &&
                  typeof colSpec === "object"
                    ? (colSpec.encoder ?? null)
                    : null;
                const renamable = Boolean(datasetId);
                const sortDir =
                  sort?.id === key ? (sort.desc ? "desc" : "asc") : null;
                return (
                  <LeanHeaderCell
                    key={key}
                    columnKey={key}
                    type={type}
                    encoder={encoder}
                    renamable={renamable}
                    isEditing={editingColumn === key}
                    sortDir={sortDir}
                    allColumnKeys={allColumnKeys}
                    datasetId={datasetId}
                    onStartEdit={() => setEditingColumn(key)}
                    onCommitEdit={handleCommitRename}
                    onCancelEdit={handleCancelRename}
                    onSortClick={() => handleSortClick(key)}
                    onEncoderChanged={onColumnChanged}
                  />
                );
              })}
            </tr>
            {enableFilters && showFilters && (
              <tr>
                {enableRowSelection && (
                  <th className="lean-th lean-th--select" />
                )}
                {visibleColumnKeys.map((key) => {
                  const type = getColType(key);
                  const operator =
                    filterOperators[key] ?? defaultOpForType(type);
                  return (
                    <LeanFilterCell
                      key={key}
                      columnKey={key}
                      type={type}
                      operator={operator}
                      value={filterValues[key]}
                      onOperatorChange={(op) =>
                        handleFilterOperatorChange(key, op)
                      }
                      onValueChange={(v) => handleFilterValueChange(key, v)}
                    />
                  );
                })}
              </tr>
            )}
          </thead>
          <tbody>
            {rows.map((row, i) => {
              const globalIndex = page * pageSize + i;
              const isChecked =
                enableRowSelection &&
                selectedRowIndices != null &&
                selectedRowIndices.has(globalIndex);
              const isSelected = selectedRowIndex === globalIndex || isChecked;
              const clickable = Boolean(onRowClick) || enableRowSelection;
              const handleRowClick = onRowClick
                ? () => onRowClick(row, globalIndex)
                : enableRowSelection
                  ? () => toggleRowSelected(globalIndex)
                  : undefined;
              return (
                <tr
                  key={i}
                  className={
                    clickable ? "lean-row lean-row--clickable" : "lean-row"
                  }
                  onClick={handleRowClick}
                  style={{
                    backgroundColor: isSelected
                      ? theme.palette.action.selected
                      : undefined,
                  }}
                >
                  {enableRowSelection && (
                    <td
                      className="lean-td lean-td--select"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Checkbox
                        size="small"
                        checked={Boolean(isChecked)}
                        onChange={() => toggleRowSelected(globalIndex)}
                      />
                    </td>
                  )}
                  {visibleColumnKeys.map((key) => (
                    <LeanCell
                      key={key}
                      value={row[key]}
                      query={highlightQuery}
                    />
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
        {!loading && rows.length === 0 && (
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ p: 4, textAlign: "center" }}
          >
            {t("datasets:table.noRows")}
          </Typography>
        )}
      </div>
      <TablePagination
        component="div"
        sx={{
          backgroundColor: "var(--lean-body-bg)",
          border: "1px solid rgba(128, 128, 128, 0.3)",
          borderTop: "none",
          borderBottomLeftRadius: 4,
          borderBottomRightRadius: 4,
        }}
        count={total}
        page={page}
        rowsPerPage={pageSize}
        showFirstButton
        showLastButton
        onPageChange={(_e, p) => setPage(p)}
        onRowsPerPageChange={(e) => {
          setPageSize(parseInt(e.target.value, 10));
          setPage(0);
        }}
        rowsPerPageOptions={enableRowsPerPage ? [10, 25, 50] : [pageSize]}
        labelRowsPerPage={enableRowsPerPage ? undefined : ""}
        slotProps={
          enableRowsPerPage
            ? undefined
            : { select: { sx: { display: "none" } } }
        }
      />
    </Box>
  );
}

LeanDatasetTable.propTypes = {
  fetchPage: PropTypes.func.isRequired,
  initialPageSize: PropTypes.number,
  deps: PropTypes.array,
  columnTypes: PropTypes.object,
  datasetId: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  datasetPath: PropTypes.string,
  datasetName: PropTypes.string,
  onColumnChanged: PropTypes.func,
  enableFilters: PropTypes.bool,
  enableSearch: PropTypes.bool,
  enableRowsPerPage: PropTypes.bool,
  enableColumnVisibility: PropTypes.bool,
  showExportButton: PropTypes.bool,
  onRowClick: PropTypes.func,
  selectedRowIndex: PropTypes.number,
  enableRowSelection: PropTypes.bool,
  selectedRowIndices: PropTypes.instanceOf(Set),
  onRowSelectionChange: PropTypes.func,
};

export default LeanDatasetTable;
