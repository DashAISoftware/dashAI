import React, { useCallback } from "react";
import {
  DialogContentText,
  Grid,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import PropTypes from "prop-types";

import FormSchema from "../shared/FormSchema";
import FormSchemaLayout from "../shared/FormSchemaLayout";
import { useTranslation } from "react-i18next";

function ConfigureExplainerStep({
  newExpl,
  setNewExpl,
  setNextEnabled,
  formSubmitRef,
  scope,
}) {
  const { t } = useTranslation(["explainers"]);
  const handleErrorChange = useCallback(
    (hasError) => {
      setNextEnabled(!hasError);
    },
    [setNextEnabled],
  );

  function filterFitParameters(explainer) {
    const prefix = "fit_parameter_";
    return Object.keys(explainer).reduce(
      (result, key) => {
        if (key.startsWith(prefix)) {
          result.fitParameters[key.slice(prefix.length)] = explainer[key];
        } else {
          result.parameters[key] = explainer[key];
        }
        return result;
      },
      { parameters: {}, fitParameters: {} },
    );
  }

  const handleUpdateParameters = (values) => {
    if (scope === "Local") {
      const { parameters, fitParameters } = filterFitParameters(values);
      setNewExpl((_) => ({
        ...newExpl,
        parameters: parameters,
        fit_parameters: fitParameters,
      }));
    } else {
      setNewExpl((_) => ({ ...newExpl, parameters: values }));
    }
  };

  return (
    <Grid
      container
      direction="row"
      justifyContent="space-around"
      alignItems="stretch"
      spacing={3}
    >
      <Grid size={{ xs: 12 }}>
        <Typography variant="h5" component="h3">
          {t("explainers:label.configureExplainer")}
        </Typography>
      </Grid>
      {/* Configure dataloader parameters */}
      <Grid size={{ xs: 12, md: 6 }}>
        <Paper
          variant="outlined"
          sx={{ p: 4, maxHeight: "55vh", overflow: "auto" }}
        >
          <Stack spacing={3}>
            <DialogContentText>
              {t("explainers:label.explainerConfiguration")}
            </DialogContentText>

            <FormSchemaLayout>
              <FormSchema
                autoSave
                model={newExpl.explainer_name}
                onFormSubmit={(values) => {
                  handleUpdateParameters(values);
                }}
                onValuesChange={(values) => {
                  handleUpdateParameters(values);
                }}
                setError={handleErrorChange}
                formSubmitRef={formSubmitRef}
              />
            </FormSchemaLayout>
          </Stack>
        </Paper>
      </Grid>
    </Grid>
  );
}

ConfigureExplainerStep.propTypes = {
  newExpl: PropTypes.shape({
    name: PropTypes.string,
    explainer_name: PropTypes.string,
    dataset_id: PropTypes.number,
    parameters: PropTypes.object,
    fit_parameters: PropTypes.object,
  }),
  setNewExpl: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
  formSubmitRef: PropTypes.shape({ current: PropTypes.any }).isRequired,
};

export default ConfigureExplainerStep;
