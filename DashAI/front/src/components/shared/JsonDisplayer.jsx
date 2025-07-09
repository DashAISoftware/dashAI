import React from "react";
import PropTypes from "prop-types";

import { Grid, Typography } from "@mui/material";

import NestedListDisplayer from "./NestedListDisplayer";

/**
 * Display JSON data in a nested list or JSON format
 * @param {string} displayMode - Display mode: "nested-list" or "json"
 * @param {string} name - Name of the JSON data
 * @param {object|array} data - JSON data to display
 * @returns
 */
function JsonDisplayer({ displayMode = "nested-list", name, data }) {
  return (
    <Grid item>
      {displayMode === "nested-list" && (
        <NestedListDisplayer
          name={name}
          value={data}
          initialState={{ open: true }}
        />
      )}

      {displayMode === "json" && (
        <Typography variant="body1" component="pre">
          {JSON.stringify(data, null, 4)}
        </Typography>
      )}
    </Grid>
  );
}

JsonDisplayer.propTypes = {
  displayMode: PropTypes.oneOf(["nested-list", "json"]).isRequired,
  name: PropTypes.string.isRequired,
  data: PropTypes.oneOfType([
    PropTypes.objectOf(
      PropTypes.oneOfType([
        PropTypes.string,
        PropTypes.number,
        PropTypes.bool,
        PropTypes.object,
        PropTypes.array,
      ]),
    ),
    PropTypes.arrayOf(
      PropTypes.oneOfType([
        PropTypes.string,
        PropTypes.number,
        PropTypes.bool,
        PropTypes.object,
        PropTypes.array,
      ]),
    ),
  ]).isRequired,
};

export default JsonDisplayer;
