import React from "react";
import PropTypes from "prop-types";
import {
  Box,
  Collapse,
  Table,
  TableBody,
  TableCell,
  TableRow,
  Typography,
} from "@mui/material";
import { ExpandLess, ExpandMore } from "@mui/icons-material";

// Unwrap properties wrappers and single-entry model params to reach the leaf model.
// e.g. {properties: {component: "TaskModel", params: {comp: {component: "SVC", params: {...}}}}}
// → {component: "SVC", params: {...}}
function unwrapToLeafModel(value) {
  if (typeof value !== "object" || value === null) return value;
  if ("properties" in value) return unwrapToLeafModel(value.properties);
  if ("component" in value && "params" in value) {
    const entries = Object.entries(value.params);
    if (entries.length === 1) {
      const inner = entries[0][1];
      if (
        typeof inner === "object" &&
        inner !== null &&
        "component" in inner &&
        "params" in inner
      ) {
        return unwrapToLeafModel(inner);
      }
    }
  }
  return value;
}

export function renderParamValue(value) {
  if (typeof value !== "object" || value === null) {
    return String(value);
  }
  if ("fixed_value" in value) {
    return String(value.fixed_value);
  }
  const unwrapped = unwrapToLeafModel(value);
  if (
    typeof unwrapped === "object" &&
    unwrapped !== null &&
    "component" in unwrapped &&
    "params" in unwrapped
  ) {
    return (
      <ModelParamBlock
        component={unwrapped.component}
        params={unwrapped.params}
      />
    );
  }
  return JSON.stringify(value);
}

function ModelParamBlock({ component, params }) {
  const [open, setOpen] = React.useState(false);
  return (
    <Box>
      <Box
        onClick={() => setOpen((v) => !v)}
        sx={{
          display: "inline-flex",
          alignItems: "center",
          gap: 0.5,
          cursor: "pointer",
          userSelect: "none",
          "&:hover": { opacity: 0.75 },
        }}
      >
        <Typography variant="caption" fontWeight="bold">
          {component}
        </Typography>
        {open ? (
          <ExpandLess sx={{ fontSize: 14 }} />
        ) : (
          <ExpandMore sx={{ fontSize: 14 }} />
        )}
      </Box>
      <Collapse in={open}>
        <Table size="small" sx={{ mt: 0.5 }}>
          <TableBody>
            {Object.entries(params).map(([k, v]) => (
              <TableRow key={k}>
                <TableCell sx={{ pl: 2, borderBottom: "none", py: 0.5 }}>
                  {k}
                </TableCell>
                <TableCell sx={{ borderBottom: "none", py: 0.5 }}>
                  {renderParamValue(v)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Collapse>
    </Box>
  );
}

ModelParamBlock.propTypes = {
  component: PropTypes.string.isRequired,
  params: PropTypes.object.isRequired,
};

export default ModelParamBlock;
