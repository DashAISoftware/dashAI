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
      <Divider sx={{ mt: 2, mb: 2, borderColor: "ui.borderLight" }} />
      <Table size="small">
        <TableBody>
          {entries.map(([key, value]) => (
            <TableRow key={key} sx={{ "&:last-child td": { borderBottom: 0 } }}>
              <TableCell
                sx={{
                  borderColor: "ui.borderLight",
                  py: 3,
                }}
              >
                <Typography
                  variant="body2"
                  sx={{
                    fontFamily: '"IBM Plex Mono", monospace',
                    color: "text.secondary",
                  }}
                >
                  {key}
                </Typography>
              </TableCell>
              <TableCell
                sx={{
                  borderColor: "ui.borderLight",
                  py: 3,
                }}
              >
                <Typography variant="body2" color="text.primary">
                  {formatValue(value)}
                </Typography>
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
