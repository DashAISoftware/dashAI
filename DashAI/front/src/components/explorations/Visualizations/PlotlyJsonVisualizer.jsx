import React from "react";
import PropTypes from "prop-types";

import Plot from "react-plotly.js";

function PlotlyJsonVisualizer({ data }) {
  return (
    <React.Fragment>
      <Plot {...data} />
    </React.Fragment>
  );
}

PlotlyJsonVisualizer.propTypes = {
  data: PropTypes.object.isRequired,
};

export default PlotlyJsonVisualizer;
