import React from "react";
import PropTypes from "prop-types";
import {
  Box,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableRow,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";

function formatValue(value) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") {
    const str = JSON.stringify(value);
    return str.length > 60 ? str.slice(0, 60) + "…" : str;
  }
  return String(value);
}

function Parameters({ data }) {
  const { t } = useTranslation(["common"]);
  const entries = data ? Object.entries(data) : [];

  return (
    <Box>
      <Typography variant="sectionLabel" sx={{ color: "text.secondary" }}>
        {t("common:parameters")}
      </Typography>
      <Divider sx={{ mt: 1, mb: 1, borderColor: "ui.borderLight" }} />
      <Table size="small">
        <TableBody>
          {entries.map(([key, value]) => (
            <TableRow key={key} sx={{ "&:last-child td": { borderBottom: 0 } }}>
              <TableCell
                sx={{
                  fontFamily: '"IBM Plex Mono", monospace',
                  fontSize: "0.8rem",
                  color: "text.secondary",
                  borderColor: "ui.borderLight",
                  py: 0.75,
                }}
              >
                {key}
              </TableCell>
              <TableCell
                sx={{
                  fontSize: "0.8rem",
                  color: "text.primary",
                  borderColor: "ui.borderLight",
                  py: 0.75,
                }}
              >
                {formatValue(value)}
              </TableCell>
            </TableRow>
          ))}
          {entries.length === 0 && (
            <TableRow>
              <TableCell colSpan={2} sx={{ borderBottom: 0 }}>
                <Typography variant="body2" color="text.disabled">
                  {t("common:noItemsAvailable")}
                </Typography>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </Box>
  );
}

Parameters.propTypes = {
  data: PropTypes.object.isRequired,
};

export default Parameters;
