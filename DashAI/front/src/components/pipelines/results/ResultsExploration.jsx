import React, { useState, useEffect } from "react";
import {
  TabularVisualizer,
  PlotlyJsonVisualizer,
  ImageVisualizer,
} from "../../explorations/Visualizations";
import { Box, Typography, Tooltip } from "@mui/material";
import { getExplorationResults } from "../../../api/pipeline";

function NullCell() {
  const [hover, setHover] = useState(false);
  return (
    <Box
      sx={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
      }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <Typography variant="body2" color="text.disabled">
        {hover ? "None" : "-"}
      </Typography>
    </Box>
  );
}

const visualizers = {
  tabular: TabularVisualizer,
  plotly_json: PlotlyJsonVisualizer,
  image_base64: ImageVisualizer,
  image_url: ImageVisualizer,
};

const visualizersKeys = {
  tabular: "tabular",
  plotly_json: "plotly_json",
  image_base64: "image_base64",
  image_url: "image_url",
};

const ORIENTATIONS = {
  dict: "dict",
  records: "records",
};

const getDataFromOrientation = (data, orientation) => {
  let res = {
    columns: [],
    rows: [],
  };

  if (orientation === ORIENTATIONS.records) {
    throw new Error(`orientation ${orientation} not supported`);
  }

  if (orientation === ORIENTATIONS.dict) {
    const columns = Object.keys(data);
    res.columns = [
      {
        field: "id",
        headerName: "Index",
        renderCell: (params) => (
          <Tooltip title={params.value} arrow>
            <Typography variant="body2">{params.value}</Typography>
          </Tooltip>
        ),
      },
      ...columns.map((column) => ({
        field: column,
        headerName: column,
        renderCell: (params) => {
          if (params.value === null) return <NullCell />;
          if (typeof params.value === "object") {
            const tooltip = JSON.stringify(params.value);
            return (
              <Tooltip title={tooltip} arrow>
                <Typography variant="body2" color="text.secondary">
                  {JSON.stringify(params.value)}
                </Typography>
              </Tooltip>
            );
          }
          if (
            params.value !== "" &&
            !isNaN(params.value) &&
            !Number.isInteger(params.value)
          ) {
            const display = parseFloat(params.value).toFixed(2);
            return (
              <Tooltip title={params.value} arrow>
                <Typography variant="body2">{display}</Typography>
              </Tooltip>
            );
          }
          return (
            <Tooltip title={params.value} arrow>
              <Typography variant="body2">{params.value}</Typography>
            </Tooltip>
          );
        },
      })),
    ];

    const rows = [];
    const indexes = Object.keys(data[columns[0]]);
    indexes.forEach((index) => {
      const row = { id: index };
      columns.forEach((column) => {
        row[column] = data[column][index];
      });
      rows.push(row);
    });
    res.rows = rows;
  }

  return res;
};

function Results({ pipelineId }) {
  const [explorationResults, setExplorationResults] = useState(null);

  useEffect(() => {
    const fetchResults = async () => {
      try {
        const response = await getExplorationResults(pipelineId);
        setExplorationResults(response);
      } catch (error) {
        console.error("Error fetching results:", error);
      }
    };

    if (pipelineId) {
      fetchResults();
    }
  }, [pipelineId]);

  const renderVisualizer = (type, dataObj) => {
    if (!Object.keys(visualizers).includes(type)) {
      console.error(`No visualizer found for type: ${type}`);
      return null;
    }

    if (type === visualizersKeys.tabular) {
      const data = getDataFromOrientation(dataObj.data, dataObj.config.orient);
      return (
        <TabularVisualizer key={type} columns={data.columns} rows={data.rows} />
      );
    }

    if (type === visualizersKeys.plotly_json) {
      return (
        <PlotlyJsonVisualizer key={type} data={JSON.parse(dataObj.data)} />
      );
    }

    if (type === visualizersKeys.image_base64) {
      return (
        <ImageVisualizer
          key={type}
          data={`data:image/png;base64,${dataObj.data}`}
        />
      );
    }

    if (type === visualizersKeys.image_url) {
      return <ImageVisualizer key={type} data={dataObj.data} />;
    }

    return null;
  };

  const normalizeGroupedResults = (results) => {
    if (!results || typeof results !== "object") {
      return {};
    }

    const entries = Object.entries(results);
    if (entries.length === 0) {
      return {};
    }

    const alreadyGrouped = entries.every(([, value]) => Array.isArray(value));
    if (alreadyGrouped) {
      return results;
    }

    return {
      "Unknown Dataset": entries.map(([explorationId, result]) => ({
        ...result,
        exploration_id: explorationId,
        node_id: "legacy",
      })),
    };
  };

  if (!explorationResults) {
    return <Typography variant="body2">Loading...</Typography>;
  }

  const groupedResults = normalizeGroupedResults(explorationResults);

  return (
    <Box
      sx={{
        width: "100%",
        display: "flex",
        flexDirection: "column",
        gap: 4,
        padding: 2,
      }}
    >
      {Object.entries(groupedResults).map(([datasetName, datasetResults]) => (
        <Box key={datasetName} sx={{ width: "100%", minWidth: "800px" }}>
          <Typography variant="h5" gutterBottom>
            {datasetName}
          </Typography>

          {datasetResults.map((result, i) => (
            <Box
              key={`${result.node_id}-${result.exploration_id}`}
              sx={{ width: "100%", minWidth: "800px", mb: 4 }}
            >
              <Typography gutterBottom variant="h6" color={"GrayText"}>
                {i + 1}: {result.exploration_type}
                {result.name ? ` | ${result.name}` : ""}
              </Typography>
              {result.results
                ? renderVisualizer(result.results.type, result.results)
                : null}
            </Box>
          ))}
        </Box>
      ))}
    </Box>
  );
}

export default Results;
