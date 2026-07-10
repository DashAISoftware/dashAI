import { useState, useEffect } from "react";
import { getExplorerResults } from "../../../api/explorer";
import {
  artifactToVisualizerData,
  visualizersKeys,
} from "../../../utils/artifactVisualizerData";

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
    if (!explorer?.id || explorer.status !== 3) {
      return;
    }

    setLoading(true);
    try {
      const artifacts = await getExplorerResults(explorer.id);
      const [artifact] = artifacts ?? [];
      if (!artifact?.type) {
        throw new Error("No artifacts in the response");
      }

      const visualizerData = artifactToVisualizerData(artifact);
      setDataType(visualizerData.dataType);
      setData(visualizerData.data);
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

export { visualizersKeys };
