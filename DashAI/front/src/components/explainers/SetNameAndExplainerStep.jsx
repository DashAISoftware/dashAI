import React, { useState, useEffect } from "react";
import { Box, CircularProgress, TextField, Typography } from "@mui/material";
import PropTypes from "prop-types";
import { useSnackbar } from "notistack";

import { getComponents as getComponentsRequest } from "../../api/component";
import ComponentSelector from "../custom/ComponentSelector";
import { useTranslation } from "react-i18next";

function SetNameAndExplainerStep({
  newExpl,
  setNewExpl,
  setNextEnabled,
  scope,
  taskName,
  existingExplainers = [],
  preselectedExplainerName = null,
}) {
  const { enqueueSnackbar } = useSnackbar();
  const [loading, setLoading] = useState(false);

  const [nModifications, setNModifications] = useState(0);
  const [explNameOk, setExplNameOk] = useState(false);
  const [explNameError, setExplNameError] = useState(false);
  const [explNameExistsError, setExplNameExistsError] = useState(false);

  const [explainers, setExplainers] = useState([]);
  const [selectedExplainer, setSelectedExplainer] = useState({});
  const [selectedExplainerOk, setSelectedExplainerOk] = useState(false);
  const { t } = useTranslation(["explainers"]);

  const getExplainers = async () => {
    setLoading(true);
    try {
      const result = await getComponentsRequest({
        selectTypes: [`${scope}Explainer`],
        relatedComponent: taskName,
      });
      const filtered = result.filter((obj) => !obj.name.startsWith("Fit"));
      setExplainers(filtered);
      if (preselectedExplainerName) {
        const preselected = filtered.find(
          (obj) => obj.name === preselectedExplainerName,
        );
        if (preselected) {
          setSelectedExplainer(preselected);
        }
      }
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
    } finally {
      setLoading(false);
    }
  };

  const handleNameInputChange = (event) => {
    setNewExpl({ ...newExpl, name: event.target.value });
    setNModifications(nModifications + 1);

    if (nModifications + 1 >= 4) {
      if (event.target.value.length < 4) {
        setExplNameError(true);
        setExplNameOk(false);
      } else {
        setExplNameError(false);
        setExplNameOk(true);
      }
    }
  };

  useEffect(() => {
    if (selectedExplainer && "name" in selectedExplainer) {
      setNewExpl({
        ...newExpl,
        explainer_name: selectedExplainer.name,
      });
      setSelectedExplainerOk(true);
    }
  }, [selectedExplainer]);

  useEffect(() => {
    getExplainers();
  }, []);

  useEffect(() => {
    if (typeof newExpl.name === "string" && newExpl.name.length >= 4) {
      const normalizedName = newExpl.name.trim().toLowerCase();
      const nameExists = existingExplainers.some(
        (explainer) => explainer?.name?.trim().toLowerCase() === normalizedName,
      );

      setExplNameExistsError(nameExists);
      setExplNameOk(true);
      setExplNameError(false);
      setNModifications(4);
    } else {
      setExplNameOk(false);
      setExplNameExistsError(false);
      if (nModifications >= 4) {
        setExplNameError(true);
      }
    }
  }, [newExpl.name, nModifications, existingExplainers]);

  useEffect(() => {
    if (explNameOk && selectedExplainerOk && !explNameExistsError) {
      setNextEnabled(true);
    } else {
      setNextEnabled(false);
    }
  }, [explNameOk, selectedExplainerOk, explNameExistsError]);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <TextField
        id="explainer-name-input"
        label={t("explainers:label.explainerName")}
        value={newExpl.name}
        fullWidth
        onChange={handleNameInputChange}
        autoComplete="off"
        error={explNameError || explNameExistsError}
        helperText={
          explNameExistsError
            ? t("explainers:error.nameAlreadyExists", {
                defaultValue: "Name already exists",
              })
            : explNameError
              ? t("explainers:error.nameTooShort")
              : ""
        }
      />

      <Typography variant="subtitle2">
        {t("explainers:label.selectExplainer")}
      </Typography>

      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <ComponentSelector
          components={explainers}
          selected={selectedExplainer?.name ? selectedExplainer : null}
          onSelect={setSelectedExplainer}
          flat
          searchPlaceholder={t("explainers:label.searchExplainers", {
            defaultValue: "Search explainers...",
          })}
        />
      )}
    </Box>
  );
}

SetNameAndExplainerStep.propTypes = {
  newExpl: PropTypes.shape({
    name: PropTypes.string,
    explainer_name: PropTypes.string,
    dataset_id: PropTypes.number,
    parameters: PropTypes.object,
    fit_parameters: PropTypes.object,
  }),
  setNewExpl: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
  scope: PropTypes.string.isRequired,
  taskName: PropTypes.string,
  existingExplainers: PropTypes.array,
  preselectedExplainerName: PropTypes.string,
};

export default SetNameAndExplainerStep;
