import React from "react";
import PropTypes from "prop-types";
import { Box, Typography, Divider, TextField, Alert } from "@mui/material";
import { useTranslation } from "react-i18next";
import FormSchemaWithSelectedModel from "../shared/FormSchemaWithSelectedModel";
import FormSchemaContainer from "../shared/FormSchemaContainer";
import OptimizationTableSelectOptimizer from "./modelSession/OptimizationTableSelectOptimizer";
import ModelsTableSelectMetric from "./modelSession/ModelsTableSelectMetric";

/**
 * The actual "edit a run's parameters" form body — run name, model
 * parameters, and optimizer configuration if any parameter is marked for
 * tuning. Shared by the "Edit Run" modal (RunEditDialog) and the model
 * detail view's sidebar (ModelConfigSidebar); each wraps it in its own
 * chrome (dialog vs. inline panel) and Save/Cancel actions.
 */
export default function RunEditForm({
  run,
  taskName,
  editedName,
  setEditedName,
  editedParameters,
  handleParametersChange,
  editedOptimizer,
  editedOptimizerParams,
  setEditedOptimizerParams,
  handleOptimizerParamsChange,
  handleOptimizerSelected,
  editedGoalMetric,
  setEditedGoalMetric,
  hasOptimizableParams,
}) {
  const { t } = useTranslation(["models", "common"]);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <Alert severity="info">
        {t("models:message.editingParametersWarning")}
      </Alert>

      <TextField
        label={t("models:label.runName")}
        value={editedName}
        onChange={(e) => setEditedName(e.target.value)}
        fullWidth
        required
        size="small"
      />

      {run.model_name && (
        <Box>
          <Typography variant="subtitle2" sx={{ mb: 2 }}>
            {t("common:modelParameters")}
          </Typography>
          <FormSchemaContainer>
            <FormSchemaWithSelectedModel
              modelToConfigure={run.model_name}
              initialValues={editedParameters}
              onFormSubmit={handleParametersChange}
              onValuesChange={handleParametersChange}
              onCancel={() => {}}
              hideButtons
            />
          </FormSchemaContainer>
        </Box>
      )}

      {hasOptimizableParams && (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <Divider />
          <Typography variant="subtitle2">
            {t("models:label.hyperparameterOptimizerConfiguration")}
          </Typography>
          <Alert severity="warning" icon={false}>
            {t("models:message.parametersMarkedForOptimization")}
          </Alert>

          <Box>
            <Typography variant="body2" sx={{ mb: 1 }}>
              {t("models:label.goalMetric")} *
            </Typography>
            <ModelsTableSelectMetric
              taskName={taskName}
              metricName={editedGoalMetric}
              handleSelectedMetric={setEditedGoalMetric}
              required
            />
          </Box>

          <OptimizationTableSelectOptimizer
            taskName={taskName}
            optimizerName={editedOptimizer}
            handleSelectedOptimizer={handleOptimizerSelected}
          />

          {editedOptimizer && (
            <Box>
              <Typography variant="subtitle2" sx={{ mb: 2 }}>
                {t("common:optimizerParameters")}
              </Typography>
              <FormSchemaContainer>
                <FormSchemaWithSelectedModel
                  modelToConfigure={editedOptimizer}
                  initialValues={editedOptimizerParams}
                  onFormSubmit={(values) => setEditedOptimizerParams(values)}
                  onValuesChange={handleOptimizerParamsChange}
                  onCancel={() => {}}
                  hideButtons
                />
              </FormSchemaContainer>
            </Box>
          )}
        </Box>
      )}
    </Box>
  );
}

RunEditForm.propTypes = {
  run: PropTypes.shape({
    model_name: PropTypes.string,
  }).isRequired,
  taskName: PropTypes.string,
  editedName: PropTypes.string.isRequired,
  setEditedName: PropTypes.func.isRequired,
  editedParameters: PropTypes.object.isRequired,
  handleParametersChange: PropTypes.func.isRequired,
  editedOptimizer: PropTypes.string.isRequired,
  editedOptimizerParams: PropTypes.object.isRequired,
  setEditedOptimizerParams: PropTypes.func.isRequired,
  handleOptimizerParamsChange: PropTypes.func.isRequired,
  handleOptimizerSelected: PropTypes.func.isRequired,
  editedGoalMetric: PropTypes.string.isRequired,
  setEditedGoalMetric: PropTypes.func.isRequired,
  hasOptimizableParams: PropTypes.bool.isRequired,
};
