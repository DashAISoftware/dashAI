import React from "react";
import PropTypes from "prop-types";
import {
  Box,
  Table,
  TableBody,
  TableCell,
  TableRow,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";

/**
 * Renders the original dataset row given to the model for one explained
 * instance: the input image for image tasks, or a feature name/value table
 * for tabular and text tasks. Returns null when there is nothing to show.
 */
export default function ModelInputView({ input, columns = [] }) {
  const { t } = useTranslation(["common"]);

  if (!input) return null;

  if (input.kind === "image") {
    if (!input.data) return null;
    return (
      <Box
        component="img"
        src={`data:${input.mime || "image/png"};base64,${input.data}`}
        alt={t("common:image")}
        sx={{ maxWidth: "100%", maxHeight: 320, objectFit: "contain" }}
      />
    );
  }

  if (input.kind === "tabular") {
    const values = input.values || [];
    return (
      <Table size="small">
        <TableBody>
          {columns.map((column, i) => (
            <TableRow key={column}>
              <TableCell sx={{ fontWeight: 600, width: "40%", border: 0 }}>
                {column}
              </TableCell>
              <TableCell sx={{ border: 0 }}>
                {values[i] === null || values[i] === undefined
                  ? "-"
                  : String(values[i])}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    );
  }

  return (
    <Typography variant="body2" sx={{ whiteSpace: "pre-line" }}>
      {typeof input.text === "string" ? input.text : ""}
    </Typography>
  );
}

ModelInputView.propTypes = {
  input: PropTypes.shape({
    kind: PropTypes.string,
    data: PropTypes.string,
    mime: PropTypes.string,
    values: PropTypes.array,
    text: PropTypes.string,
  }),
  columns: PropTypes.arrayOf(PropTypes.string),
};
