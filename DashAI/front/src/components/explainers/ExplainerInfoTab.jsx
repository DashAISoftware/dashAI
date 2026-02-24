import { Divider, Grid, Typography } from "@mui/material";
import React from "react";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import { formatDate } from "../../utils";

/**
 * Component that displays general information associated with a explainer.
 * @param {object} explainerData object that contains all the necesary info of the explainer
 */
function ExplainerInfoTab({ explainerData }) {
  const { t } = useTranslation(["explainers", "common"]);

  const explainerInfo = [
    { key: "id", label: t("common:id") },
    { key: "name", label: t("common:name") },
    { key: "run_id", label: t("explainers:label.runId") },
    { key: "explainer_name", label: t("explainers:label.explainerName") },
    { key: "dataset_id", label: t("explainers:label.datasetId") },
    { key: "explanation_path", label: t("explainers:label.explanationPath") },
    { key: "plot_path", label: t("explainers:label.plotPath") },
    { key: "status", label: t("common:status") },
  ];

  const explainerDateInfo = [{ key: "created", label: t("common:created") }];

  return (
    <Grid container direction="column">
      {/* Explainer name related info */}
      <Grid>
        <Grid
          container
          direction="row"
          alignItems="center"
          rowSpacing={3}
          columnSpacing={15}
        >
          {explainerInfo.map((param) => (
            <Grid key={param.key}>
              <Typography variant="subtitle1">{param.label}</Typography>
              <Typography variant="p" sx={{ color: "gray" }}>
                {explainerData[param.key] ?? "-"}
              </Typography>
            </Grid>
          ))}
        </Grid>
      </Grid>

      <Divider sx={{ mt: 3, mb: 3 }} />

      {/* Explainer Date related info */}
      <Grid>
        <Grid
          container
          direction="row"
          alignItems="center"
          rowSpacing={3}
          columnSpacing={15}
        >
          {explainerDateInfo.map((param) => (
            <Grid key={param.key}>
              <Typography variant="subtitle1">{param.label}</Typography>
              <Typography variant="p" sx={{ color: "gray" }}>
                {formatDate(explainerData[param.key] ?? "-")}
              </Typography>
            </Grid>
          ))}
        </Grid>
      </Grid>
    </Grid>
  );
}

ExplainerInfoTab.propTypes = {
  explainerData: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    run_id: PropTypes.number,
    explainer_name: PropTypes.string,
    dataset_id: PropTypes.number,
    explanation_path: PropTypes.string,
    plot_path: PropTypes.string,
    parameters: PropTypes.object,
    created: PropTypes.string,
    status: PropTypes.number,
  }).isRequired,
};

export default ExplainerInfoTab;
