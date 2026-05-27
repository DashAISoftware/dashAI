import React from "react";
import PropTypes from "prop-types";
import { Grid, Typography } from "@mui/material";

import { runDateInfo } from "../constants/runDateInfo";
import { formatDate } from "../constants/formatDate";

function ResultsTabInfoDate({ runData }) {
  return (
    <Grid>
      <Grid
        container
        direction="row"
        alignItems="center"
        rowSpacing={6}
        columnSpacing={30}
      >
        {runDateInfo.map((param) => (
          <Grid key={param.key}>
            <Typography variant="subtitle1">{param.label}</Typography>
            <Typography variant="p" sx={{ color: "gray" }}>
              {formatDate(runData[param.key] ?? "-")}
            </Typography>
          </Grid>
        ))}
      </Grid>
    </Grid>
  );
}

ResultsTabInfoDate.propTypes = {
  runData: PropTypes.object.isRequired,
};

export default ResultsTabInfoDate;
