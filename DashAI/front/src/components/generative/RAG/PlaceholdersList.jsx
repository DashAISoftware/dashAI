import React from "react";
import Typography from "@mui/material/Typography";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import Tooltip from "@mui/material/Tooltip";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";

export default function PlaceholdersList({
  required = [],
  optional = [],
  descriptions = {},
  template = "",
}) {
  return (
    <div style={{ marginTop: 16, marginBottom: 16 }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 64 }}>
        <div>
          <Typography variant="subtitle1" gutterBottom>
            Required Placeholders
          </Typography>
          <ul style={{ marginTop: 0 }}>
            {required.map((ph) => {
              const isPresent = template.includes(ph);
              return (
                <li
                  key={ph}
                  style={{ display: "flex", alignItems: "center", gap: 8 }}
                >
                  {isPresent ? (
                    <CheckCircleIcon fontSize="small" color="success" />
                  ) : (
                    <WarningAmberIcon fontSize="small" color="warning" />
                  )}
                  <strong>{ph}</strong>
                  <Tooltip title={descriptions[ph] || ""} placement="right">
                    <HelpOutlineIcon
                      fontSize="small"
                      color="action"
                      style={{ cursor: "pointer" }}
                    />
                  </Tooltip>
                </li>
              );
            })}
          </ul>
        </div>
        <div>
          <Typography variant="subtitle1" gutterBottom>
            Optional Placeholders
          </Typography>
          <ul style={{ marginTop: 0 }}>
            {optional.map((ph) => {
              const isPresent = template.includes(ph);
              return (
                <li
                  key={ph}
                  style={{ display: "flex", alignItems: "center", gap: 8 }}
                >
                  {isPresent && (
                    <CheckCircleIcon fontSize="small" color="success" />
                  )}
                  <strong>{ph}</strong>
                  <Tooltip title={descriptions[ph] || ""} placement="right">
                    <HelpOutlineIcon
                      fontSize="small"
                      color="action"
                      style={{ cursor: "pointer" }}
                    />
                  </Tooltip>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </div>
  );
}
