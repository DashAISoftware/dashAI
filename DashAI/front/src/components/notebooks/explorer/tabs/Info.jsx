import React from "react";
import PropTypes from "prop-types";

import { Divider, Grid, Typography } from "@mui/material";
import { formatDate } from "../../../../utils";
import { useTranslation } from "react-i18next";

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
function Info({ data, nameRelatedInfo, dateRelatedInfo }) {
  const { t } = useTranslation(["common", "datasets"]);

  const nameInfo = [
    { key: "name", label: t("common:name") },
    { key: "exploration_type", label: t("datasets:label.explorationType") },
    { key: "status", label: t("common:status") },
    { key: "exploration_path", label: t("datasets:label.explorationPath") },
  ];

  const dateInfo = [
    { key: "created", label: t("common:created") },
    { key: "last_modified", label: t("common:lastModified") },
    { key: "delivery_time", label: t("common:deliveryTime") },
    { key: "start_time", label: t("common:startTime") },
    { key: "end_time", label: t("common:endTime") },
  ];

  nameRelatedInfo = nameRelatedInfo || nameInfo;
  dateRelatedInfo = dateRelatedInfo || dateInfo;

  return (
    <Grid container direction="column">
      {/* name related info */}
      <Grid>
        <Grid
          container
          direction="row"
          alignItems="center"
          rowSpacing={3}
          columnSpacing={15}
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

      <Divider sx={{ mt: 3, mb: 3 }} />

      {/* Run Date related info */}
      <Grid>
        <Grid
          container
          direction="row"
          alignItems="center"
          rowSpacing={3}
          columnSpacing={15}
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
