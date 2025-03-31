import { useState, useEffect } from "react";
import { getComponents as getComponentsRequest } from "../api/component";
import { useSnackbar } from "notistack";

export default function useOptimizersByTask({ taskName }) {
  const [compatibleMetrics, setCompatibleMetrics] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const { enqueueSnackbar } = useSnackbar();

  const getCompatibleMetrics = async () => {
    setLoading(true);
    try {
      const metrics = await getComponentsRequest({
        selectTypes: ["Metric"],
        relatedComponent: taskName,
      });
      setCompatibleMetrics(metrics);
      setError(null);
    } catch (error) {
      enqueueSnackbar("Error while trying to obtain compatible Metrics");
      if (error.response) {
        console.error("Response error:", error.message);
      } else if (error.request) {
        console.error("Request error", error.request);
      } else {
        console.error("Unknown Error", error.message);
      }
      setError(error);
    } finally {
      setLoading(false);
    }
  };

  // in mount, fetches the compatible models with the previously selected task
  useEffect(() => {
    getCompatibleMetrics();
  }, []);

  return { compatibleMetrics, loading, error };
}
