import React from "react";
import PropTypes from "prop-types";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

/**
 * Simple selectable table built on CSS grid.
 *
 * @param {array} columns list of `{ key, label, width, align, render }`.
 *   `width` is a grid track (default "1fr"); `render(row, selected)`
 *   customizes the cell, otherwise `row[key]` is shown.
 * @param {array} rows data rows; each one must have a unique `id`
 * @param {string|number} selectedId id of the highlighted row
 * @param {func} onRowClick called with the clicked row
 * @param {string} actionLabel when given, appends a right-aligned
 *   "Detalles" column showing this text on every row
 */
export default function DataTable({
  columns,
  rows,
  selectedId,
  onRowClick,
  actionLabel,
}) {
  const theme = useTheme();

  const allColumns = actionLabel
    ? [
        ...columns,
        {
          key: "__action",
          label: "Detalles",
          width: "100px",
          align: "right",
          render: () => (
            <Typography
              variant="body2"
              sx={{ color: theme.palette.primary.main, fontSize: "0.8rem" }}
            >
              {actionLabel}
            </Typography>
          ),
        },
      ]
    : columns;

  const gridTemplateColumns = allColumns
    .map((column) => column.width ?? "1fr")
    .join(" ");

  return (
    <Box
      sx={{
        width: "100%",
        border: `1px solid ${theme.palette.divider}`,
        borderRadius: 1,
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns,
          alignItems: "center",
          px: 3,
          py: 2,
          borderBottom: `1px solid ${theme.palette.divider}`,
          background: theme.palette.background.box,
        }}
      >
        {allColumns.map((column) => (
          <Typography
            key={column.key}
            variant="caption"
            sx={{
              color: theme.palette.text.disabled,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              textAlign: column.align ?? "left",
            }}
          >
            {column.label}
          </Typography>
        ))}
      </Box>

      {/* Rows */}
      {rows.map((row) => {
        const selected = selectedId === row.id;

        return (
          <Box
            key={row.id}
            onClick={onRowClick ? () => onRowClick(row) : undefined}
            sx={{
              display: "grid",
              gridTemplateColumns,
              alignItems: "center",
              px: 3,
              py: 2.5,
              borderBottom: `1px solid ${theme.palette.divider}`,
              background: selected ? theme.palette.ui.hover : "transparent",
              cursor: onRowClick ? "pointer" : "default",
              transition: "background 0.15s",

              "&:hover": {
                background: theme.palette.ui.hover,
              },

              "&:last-child": {
                borderBottom: "none",
              },
            }}
          >
            {allColumns.map((column) => (
              <Box
                key={column.key}
                sx={{
                  minWidth: 0,
                  display: "flex",
                  justifyContent:
                    column.align === "right" ? "flex-end" : "flex-start",
                }}
              >
                {column.render ? (
                  column.render(row, selected)
                ) : (
                  <Typography
                    variant="body2"
                    sx={{ color: theme.palette.text.secondary }}
                  >
                    {row[column.key]}
                  </Typography>
                )}
              </Box>
            ))}
          </Box>
        );
      })}
    </Box>
  );
}

DataTable.propTypes = {
  columns: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string.isRequired,
      label: PropTypes.node.isRequired,
      width: PropTypes.string,
      align: PropTypes.oneOf(["left", "right"]),
      render: PropTypes.func,
    }),
  ).isRequired,
  rows: PropTypes.arrayOf(PropTypes.object).isRequired,
  selectedId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  onRowClick: PropTypes.func,
  actionLabel: PropTypes.node,
};
