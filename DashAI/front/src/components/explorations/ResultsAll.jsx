import React, { useState } from "react";
import PropTypes from "prop-types";

import { Grid, Paper, Typography } from "@mui/material";

import { ExplorerStatus } from "../../types/explorer";
import { useExplorationsContext } from "./context";
import Results from "./explorers/DetailTabs/Results";

/**
 * Component that displays the results of all explorers that have finished.
 * @param {object} props
 * @param {boolean} props.updateFlag - Flag to force update the component.
 * @param {function} props.setUpdateFlag - Function to set the update flag.
 */
function ResultsAll({ updateFlag = false, setUpdateFlag = () => {} }) {
  const { explorationData } = useExplorationsContext();
  const { explorers } = explorationData;

  const [filteredExplorers] = useState(
    explorers.filter((explorer) => explorer.status === ExplorerStatus.FINISHED),
  );

  return (
    <React.Fragment>
      <Paper
        sx={{
          display: "flex",
          flexDirection: "column",
          px: 3,
          py: 2,
          width: "100%",
        }}
        // solves a mui problem related to putting datagrid inside another datagrid
        onClick={(event) => {
          event.target = document.body;
        }}
      >
        <Grid container direction="column" spacing={2}>
          {filteredExplorers.map((explorer) => (
            <Grid item key={explorer.id} width={"100%"}>
              <Typography variant="h6" color={"GrayText"}>
                {explorer.id} {` : ${explorer.exploration_type}`}{" "}
                {explorer.name && `| ${explorer.name}`}
              </Typography>
              <Results
                id={explorer.id}
                updateFlag={updateFlag}
                setUpdateFlag={setUpdateFlag}
              />
            </Grid>
          ))}
        </Grid>
      </Paper>
    </React.Fragment>
  );
}

ResultsAll.propTypes = {
  updateFlag: PropTypes.bool,
  setUpdateFlag: PropTypes.func,
};

export default ResultsAll;
