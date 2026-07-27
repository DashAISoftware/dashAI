import React, { useMemo } from "react";
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { useTheme, alpha } from "@mui/material/styles";
import Plot from "react-plotly.js";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";

import { applyThemeToLayout } from "../../utils/plotlyTheme";

/**
 * Renders a single typed artifact ({type, payload, title}) returned by the
 * backend (explainer plots, explorer results). Supported types: "plotly"
 * (payload: plotly JSON string), "table" (payload: {columns, rows,
 * highlight}), "image" (payload: {data, mime}) and "text" (payload: string).
 * Unknown types fall back to preformatted text so nothing is silently lost.
 */
export default function ArtifactRenderer({ artifact }) {
  const theme = useTheme();
  const { t } = useTranslation(["common"]);

  const parsedFigure = useMemo(() => {
    if (artifact.type !== "plotly") return null;
    try {
      return typeof artifact.payload === "string"
        ? JSON.parse(artifact.payload)
        : artifact.payload;
    } catch (error) {
      console.error("Invalid plotly artifact payload", error);
      return null;
    }
  }, [artifact]);

  const themedLayout = useMemo(() => {
    if (!parsedFigure) return {};
    return applyThemeToLayout(parsedFigure.layout, theme);
  }, [parsedFigure, theme]);

  const highlightedCells = useMemo(() => {
    if (artifact.type !== "table") return new Set();
    const cells = artifact.payload?.highlight ?? [];
    return new Set(cells.map((cell) => `${cell.row}-${cell.column}`));
  }, [artifact]);

  const renderContent = () => {
    switch (artifact.type) {
      case "plotly":
        if (!parsedFigure) return null;
        return (
          <Plot
            data={parsedFigure.data}
            layout={{ ...themedLayout, height: 380, autosize: true }}
            config={{ displayModeBar: false }}
            useResizeHandler
            style={{ width: "100%" }}
          />
        );
      case "table": {
        const { columns = [], rows = [] } = artifact.payload ?? {};
        return (
          <TableContainer component={Paper} sx={{ maxHeight: 380 }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  {columns.map((column) => (
                    <TableCell key={column}>{column}</TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((row, rowIndex) => (
                  <TableRow key={rowIndex}>
                    {row.map((value, columnIndex) => (
                      <TableCell
                        key={columnIndex}
                        sx={
                          highlightedCells.has(`${rowIndex}-${columnIndex}`)
                            ? {
                                bgcolor: alpha(
                                  theme.palette.warning.main,
                                  0.25,
                                ),
                                fontWeight: "bold",
                              }
                            : undefined
                        }
                      >
                        {value === null ? "-" : String(value)}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        );
      }
      case "image": {
        const { data = "", mime = "image/png" } = artifact.payload ?? {};
        return (
          <Box
            component="img"
            src={`data:${mime};base64,${data}`}
            alt={artifact.title || t("common:image")}
            sx={{ maxWidth: "100%", maxHeight: 380, objectFit: "contain" }}
          />
        );
      }
      case "text":
      default:
        return (
          <Typography variant="body2" sx={{ whiteSpace: "pre-line", p: 1 }}>
            {typeof artifact.payload === "string"
              ? artifact.payload
              : JSON.stringify(artifact.payload, null, 2)}
          </Typography>
        );
    }
  };

  return (
    <Box sx={{ width: "100%" }}>
      {artifact.title && (
        <Typography variant="subtitle2" sx={{ mb: 1 }}>
          {artifact.title}
        </Typography>
      )}
      {renderContent()}
    </Box>
  );
}

ArtifactRenderer.propTypes = {
  artifact: PropTypes.shape({
    type: PropTypes.string.isRequired,
    payload: PropTypes.any,
    title: PropTypes.string,
  }).isRequired,
};
