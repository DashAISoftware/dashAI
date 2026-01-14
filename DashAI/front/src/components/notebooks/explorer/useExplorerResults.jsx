import { Box, Typography, Tooltip } from "@mui/material";
import { useState, useEffect } from "react";
import { getExplorerResults } from "../../../api/explorer";
import ImageVisualizer from ".//visualizations/ImageVisualizer";
import PlotlyJsonVisualizer from "./visualizations/PlotlyJsonVisualizer";
import TabularVisualizer from "./visualizations/TabularVisualizer";
import { getExplorerStatus } from "../../../utils/explorerStatus";
import { useTranslation } from "react-i18next";

/**
 * NullCell component to render null values in the tabular visualizer
 * @param {Object} props
 */
function NullCell({}) {
  const [hover, setHover] = useState(false);
  const { t } = useTranslation(["common"]);
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
        {hover ? t("common:none") : "-"}
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

/**
 * Hook to manage explorer results data
 * @param {Number} id The id of the exploration
 * @returns {Object} { loading, data, dataType, fetchExplorerResults }
 */
export function useExplorerResults(explorer) {
  const [loading, setLoading] = useState(false);
  const [dataType, setDataType] = useState(null);
  const [data, setData] = useState(null);

  const fetchExplorerResults = async () => {
    // Only fetch if explorer exists and has finished status
    if (!explorer?.id || getExplorerStatus(explorer.status) !== "Finished") {
      return;
    }

    setLoading(true);
    try {
      const results = await getExplorerResults(explorer.id);
      if (!results?.type) {
        throw new Error("No result type specified in the response");
      }

      // Check if there is an appropriate visualizer
      if (!Object.keys(visualizers).includes(results.type)) {
        throw new Error(`No visualizer found for type: ${results.type}`);
      }

      setDataType(results.type);

      // Process data based on type
      if (results.type === visualizersKeys.tabular) {
        const processedData = getDataFromOrientation(
          results.data,
          results.config.orient,
        );
        setData({
          columns: processedData.columns,
          rows: processedData.rows,
        });
      } else if (results.type === visualizersKeys.plotly_json) {
        setData(JSON.parse(results.data));
      } else if (
        results.type === visualizersKeys.image_base64 ||
        results.type === visualizersKeys.image_url
      ) {
        setData(results.data);
      }
    } catch (error) {
      console.error("Error fetching explorer results:", error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // Fetch the results data when explorer changes or status becomes "Finished"
  useEffect(() => {
    fetchExplorerResults();
  }, [explorer?.id, explorer?.status]);

  return {
    loading,
    data,
    setData,
    dataType,
    fetchExplorerResults,
  };
}

/**
 * Get the data from the orientation given. This function is used to transform the data
 * from the explorer results to the format required by the tabular visualizer.
 * @param {Object} data The data from the explorer results
 * @param {String} orientation The orientation of the data
 */
const getDataFromOrientation = (data, orientation) => {
  let res = {
    columns: [],
    rows: [],
  };

  if (orientation === ORIENTATIONS.records) {
    throw new Error(`orientation ${orientation} not supported`);
  }

  if (orientation === ORIENTATIONS.dict) {
    // ‘dict’ (default) : dict like {column -> {index -> value}}
    // Get the columns
    const columns = Object.keys(data);
    res.columns = [
      {
        field: "id",
        headerName: "Index",
        renderCell: (params) => {
          return (
            <Tooltip title={params.value} arrow>
              <Typography variant="body2">{params.value}</Typography>
            </Tooltip>
          );
        },
      },
      ...columns.map((column) => {
        return {
          field: column,
          headerName: column,
          renderCell: (params) => {
            if (params.value === null) {
              return <NullCell />;
            } else if (typeof params.value === "object") {
              const tooltip = JSON.stringify(params.value);
              return (
                <Tooltip title={tooltip} arrow>
                  <Typography variant="body2" color="text.secondary">
                    {JSON.stringify(params.value)}
                  </Typography>
                </Tooltip>
              );
            } else if (
              params.value !== "" &&
              !isNaN(params.value) &&
              !Number.isInteger(params.value)
            ) {
              const tooltip = params.value;
              const display = parseFloat(params.value).toFixed(2);
              return (
                <Tooltip title={tooltip} arrow>
                  <Typography variant="body2">{display}</Typography>
                </Tooltip>
              );
            }
            const tooltip = params.value;
            return (
              <Tooltip title={tooltip} arrow>
                <Typography variant="body2">{params.value}</Typography>
              </Tooltip>
            );
          },
        };
      }),
    ];

    // Get the rows
    const rows = [];
    const indexes = Object.keys(data[columns[0]]);
    indexes.forEach((index) => {
      const row = {
        id: index,
      };
      columns.forEach((column) => {
        row[column] = data[column][index];
      });
      rows.push(row);
    });
    res.rows = rows;
  }

  return res;
};

export { visualizersKeys };
