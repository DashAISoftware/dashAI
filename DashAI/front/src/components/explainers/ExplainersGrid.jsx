import { React, useEffect, useState } from "react";
import { Grid } from "@mui/material";
import { useSnackbar } from "notistack";

import { getExplainers as getExplainersRequest } from "../../api/explainer";

import ExplainersCard from "./ExplanainersCard";
import useUpdateFlag from "../../hooks/useUpdateFlag";
import { flags } from "../../constants/flags";
import { useTranslation } from "react-i18next";

/**
 * GlobalExplainersGrid
 * @returns Grid component for the explainers
 */
export default function ExplainersGrid(explainerConfig) {
  const { enqueueSnackbar } = useSnackbar();
  // const [loading, setLoading] = useState(false);
  const [explainers, setExplainers] = useState([]);
  const { runId, scope } = explainerConfig;
  const { t } = useTranslation(["explainers"]);

  // Filter explainers that have status FINISHED
  function getFilteredExplainers(explainers) {
    return explainers.filter((explainer) => explainer.status === 3);
  }

  const getExplainers = async () => {
    try {
      const explainers = await getExplainersRequest(runId, scope);
      setExplainers(explainers);
    } catch (error) {
      enqueueSnackbar(t("explainers:error.fetchExplainers"), {
        variant: "error",
      });
      if (error.response) {
        console.error("Response error:", error.message);
      } else if (error.request) {
        console.error("Request error", error.request);
      } else {
        console.error("Unknown Error", error.message);
      }
    } // finally {
    // setLoading(false);
    // }
  };

  useUpdateFlag({
    flag: flags.EXPLAINERS,
    updateFunction: getExplainers,
  });

  useEffect(() => {
    getExplainers();
  }, []);

  return (
    <Grid
      container
      flex={true}
      flexWrap={"nowrap"}
      direction={"column"}
      overflow={"auto"}
      rowGap={5}
      justifyContent="center"
      alignItems="stretch"
    >
      {getFilteredExplainers(explainers).map((explainer) => (
        <ExplainersCard
          explainer={explainer}
          key={explainer.id}
          scope={scope}
        />
      ))}
    </Grid>
  );
}
