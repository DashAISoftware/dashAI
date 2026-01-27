import React, { useState } from "react";

import { Grid, ToggleButton, ToggleButtonGroup } from "@mui/material";

import JsonDisplayer from "../../../shared/JsonDisplayer";
import { useTranslation } from "react-i18next";

/**
 * Component that displays the columns associated with an object.
 * @param {object} data object that contains all the necesary info
 */
function Columns({ data }) {
  const [displayMode, setDisplayMode] = useState("nested-list");
  const { t } = useTranslation(["common"]);

  return (
    <Grid container direction="column">
      {/* Toggle to select the mode of displaying the JSON object. */}
      <Grid>
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
          <ToggleButton value="nested-list">{t("common:list")}</ToggleButton>
          <ToggleButton value="json">{t("common:json")}</ToggleButton>
        </ToggleButtonGroup>
      </Grid>

      {/* JSON object display */}
      <JsonDisplayer
        displayMode={displayMode}
        name={t("common:columns")}
        data={data}
      />
    </Grid>
  );
}

export default Columns;
