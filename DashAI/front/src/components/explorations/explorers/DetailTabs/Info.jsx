import React from "react";
import PropTypes from "prop-types";

import { Divider, Grid, Typography } from "@mui/material";
import { formatDate } from "../../../../utils";

const nameInfo = [
  { key: "name", label: "Name" },
  { key: "exploration_type", label: "Explorer Type" },
  { key: "status", label: "Status" },
  { key: "id", label: "Explorer ID" },
  { key: "exploration_id", label: "Exploration ID" },
  { key: "exploration_path", label: "Results Path" },
];

const dateInfo = [
  { key: "created", label: "Created" },
  { key: "last_modified", label: "Last Modified" },
  { key: "delivery_time", label: "Delivery Time" },
  { key: "start_time", label: "Start Time" },
  { key: "end_time", label: "End Time" },
];

const dataToString = (data) => {
  if (data === undefined || data === null) {
    return "-";
  }

  if (data === "") {
    return "-";
  }

  return data.toString();
};

/**
 * Component that displays general information associated with an object.
 * @param {object} data object that contains all the necesary info
 */
function Info({
  data,
  nameRelatedInfo = nameInfo,
  dateRelatedInfo = dateInfo,
}) {
  return (
    <Grid container direction="column">
      {/* name related info */}
      <Grid>
        <Grid
          container
          direction="row"
          alignItems="center"
          rowSpacing={6}
          columnSpacing={30}
        >
          {nameRelatedInfo.map((param) => (
            <Grid key={param.key}>
              <Typography variant="subtitle1">{param.label}</Typography>
              <Typography variant="p" sx={{ color: "gray" }}>
                {dataToString(data[param.key])}
              </Typography>
            </Grid>
          ))}
        </Grid>
      </Grid>

      <Divider sx={{ mt: 6, mb: 6 }} />

      {/* Run Date related info */}
      <Grid>
        <Grid
          container
          direction="row"
          alignItems="center"
          rowSpacing={6}
          columnSpacing={30}
        >
          {dateRelatedInfo.map((param) => (
            <Grid key={param.key}>
              <Typography variant="subtitle1">{param.label}</Typography>
              <Typography variant="p" sx={{ color: "gray" }}>
                {data[param.key] ? formatDate(data[param.key]) : "-"}
              </Typography>
            </Grid>
          ))}
        </Grid>
      </Grid>
    </Grid>
  );
}

Info.propTypes = {
  data: PropTypes.object.isRequired,
  nameRelatedInfo: PropTypes.array,
  dateRelatedInfo: PropTypes.array,
};

export default Info;
