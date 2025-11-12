import { useMemo } from "react";
import { Typography, Tooltip } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";

/**
 * Table component to display dataset preview with inferred types in column headers.
 *
 * @param {Array} rows - Array of row objects to display
 * @param {Object} columnTypes - Object mapping column names to their inferred types
 *                                (e.g., { columnName: { type: "Categorical", dtype: "string" } })
 */
export default function PreviewDatasetTable({ rows, columnTypes }) {
  const rowsWithIds = useMemo(
    () => rows.map((row, index) => ({ id: index, ...row })),
    [rows],
  );

  const columns = useMemo(() => {
    if (!rows || rows.length === 0) return [];

    const firstRow = rows[0];
    return Object.keys(firstRow).map((field) => ({
      field,
      headerName: field,
      minWidth: 120,
      flex: 1,
      renderHeader: () => (
        <Tooltip title={field} arrow placement="top">
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              textAlign: "center",
              width: "100%",
              cursor: "help",
            }}
          >
            <Typography
              variant="subtitle2"
              style={{
                fontWeight: "bold",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                maxWidth: "100%",
              }}
            >
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
        </Tooltip>
      ),
    }));
  }, [rows, columnTypes]);

  return (
    <DataGrid
      rows={rowsWithIds}
      columns={columns}
      autoHeight
      density="compact"
      disableRowSelectionOnClick
      initialState={{
        pagination: { paginationModel: { pageSize: 5 } },
      }}
      pageSizeOptions={[5, 10]}
      columnHeaderHeight={85}
    />
  );
}
