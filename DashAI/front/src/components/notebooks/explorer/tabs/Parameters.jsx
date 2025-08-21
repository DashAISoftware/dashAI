import React, { useState } from "react";
import PropTypes from "prop-types";

import { Grid, ToggleButton, ToggleButtonGroup } from "@mui/material";

import JsonDisplayer from "../../../shared/JsonDisplayer";

/**
 * Component that displays the parameters associated with an object.
 * @param {object} data object that contains all the necesary info
 */
function Parameters({ data }) {
  const [displayMode, setDisplayMode] = useState("nested-list");

  return (
    <Grid container direction="column">
      {/* Toggle to select the mode of displaying the JSON object. */}
      <Grid item>
        <ToggleButtonGroup
          value={displayMode}
          exclusive
          onChange={(event, newMode) => {
            if (newMode !== null) {
              setDisplayMode(newMode);
            }
          }}
          sx={{ float: "right" }}
        >
          <ToggleButton value="nested-list">List</ToggleButton>
          <ToggleButton value="json">JSON</ToggleButton>
        </ToggleButtonGroup>
      </Grid>

      {/* JSON object display */}
      <JsonDisplayer displayMode={displayMode} name="Parameters" data={data} />
    </Grid>
  );
}

Parameters.propTypes = {
  data: PropTypes.object.isRequired,
};

export default Parameters;
