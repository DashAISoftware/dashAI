import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import PropTypes from "prop-types";

import { Grid, Box, Alert, AlertTitle, Chip } from "@mui/material";
import RoleColumnSelectors from "./RoleColumnSelectors";
import { getComponents as getComponentsRequest } from "../../../api/component";
import { validateColumns as validateColumnsRequest } from "../../../api/modelSession";
import { useSnackbar } from "notistack";
import { getColorByColumnType } from "../../../utils";
import { getColumnTypeLabel } from "../../../utils/typesLists";
import { useTranslation, Trans } from "react-i18next";
import {
  refToKey,
  buildStepDisplayNames,
  dropStaleGroupRefs,
  stateToOptions,
} from "./sessionColumnRefs";
import usePreprocessingStructure from "./usePreprocessingStructure";
import {
  defaultRoleSelection,
  optionsForRole,
  resolveSelection,
  selectionReady,
  selectionToRefs,
  shownRoles,
} from "./columnRoles";

/**
 * Last step of the session wizard: the final columns of every role the task
 * declares.
 *
 * Without preprocessing, every role picks from the original columns. With
 * it, a role the preprocessing may transform picks from the estimated
 * dataset state after the whole chain (see usePreprocessingStructure):
 * surviving candidate columns plus what the converters produced, each
 * represented by the synthetic key of the ColumnRef pointing at it, so the
 * selectors only ever deal with plain strings. A protected role keeps the
 * original columns it got in BaseColumnsStep and is shown fixed.
 *
 * A role that takes no columns (max 0) has no selector, and the session is
 * created without it.
 */
function SelectColumnsStep({
  newExp,
  setNewExp,
  setNextEnabled,
  dataset,
  datasetInfo,
  datasetTypes,
  taskMetadata,
  taskDisplayName,
}) {
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["experiments", "models", "common"]);

  const [convertersMeta, setConvertersMeta] = useState({});

  const roles = shownRoles(taskMetadata);
  const rawColumnNames = datasetInfo.column_names || [];
  const withPreprocessing = Boolean(newExp.applyPreprocessing);
  const steps = newExp.preprocessing || [];
  const stage1 = newExp.column_roles_stage1 || {};

  const { structure, error: structureError } = usePreprocessingStructure({
    datasetId: withPreprocessing ? dataset.id : undefined,
    taskName: newExp.task_name,
    columnRoles: stage1,
    steps,
  });

  const stepDisplayNames = buildStepDisplayNames(steps, convertersMeta);
  const finalOptions = stateToOptions(structure?.final, stepDisplayNames, t);
  // A transformable role picks from what the chain leaves; every other one
  // from the original columns.
  const baseOptionsFor = (role) =>
    withPreprocessing && role.transformable
      ? finalOptions.allKeys
      : rawColumnNames;
  // A protected role keeps its dataset type; a transformable one takes its
  // type after the chain (e.g. a column cast in place by TypeCast).
  const columnTypesForSelector = withPreprocessing
    ? { ...datasetTypes, ...finalOptions.columnTypes }
    : datasetTypes;
  const optionLabels = withPreprocessing ? finalOptions.optionLabels : {};
  const fixedRole = (role) => withPreprocessing && !role.transformable;

  // A converter output is keyed by its step's position, so a pick made for
  // another chain (the user went back and changed it) could silently point
  // at a different converter's output: those picks are dropped.
  const [selectionState, setSelection] = useState(() =>
    Object.fromEntries(
      Object.entries(
        dropStaleGroupRefs(
          newExp.column_roles || {},
          newExp.column_roles_steps,
          steps,
        ),
      ).map(([name, refs]) => [name, refs.map(refToKey)]),
    ),
  );

  // With preprocessing, a protected role is what BaseColumnsStep gave it.
  // Only what can still be picked is kept: going back and changing the
  // chain can consume a column picked here before, and turning
  // preprocessing off leaves only original columns.
  const optionsKnown = withPreprocessing
    ? Boolean(structure)
    : rawColumnNames.length > 0;
  const withFixed = {
    ...selectionState,
    ...Object.fromEntries(
      roles
        .filter(fixedRole)
        .map((role) => [role.name, stage1[role.name] || []]),
    ),
  };
  const selection = resolveSelection(
    roles,
    optionsKnown
      ? Object.fromEntries(
          roles.map((role) => [
            role.name,
            (withFixed[role.name] || []).filter((key) =>
              baseOptionsFor(role).includes(key),
            ),
          ]),
        )
      : withFixed,
  );

  // With preprocessing, the options and their defaults arrive with the
  // estimated structure, after the step has already rendered: until then an
  // empty selection is not a user mistake, so no validation error (alert or
  // "Required") may show. useLayoutEffect cannot hide this gap, since it
  // cannot wait for a network response.
  // When the structure cannot be estimated nothing can be checked, and the
  // step says so instead of waiting for it forever.
  const structureMissing = withPreprocessing && !structure;
  const awaitingStructure = structureMissing && !structureError;
  const columnsReady =
    roles.length > 0 && selectionReady(roles, selection) && !structureMissing;
  // The backend's answer, with the selection it was about. An answer only
  // counts for the selection on screen, so a selection changed since, or an
  // answer that arrives after a newer one, never enables Create.
  const [validated, setValidated] = useState({ key: null, valid: false });
  const [validationError, setValidationError] = useState(null);
  const [validationPending, setValidationPending] = useState(true);
  const latestValidation = useRef(null);

  useLayoutEffect(() => {
    // Without preprocessing, default the first time the dataset's columns
    // and the task's roles are known.
    if (withPreprocessing || rawColumnNames.length === 0 || !roles.length) {
      return;
    }
    if (Object.values(selectionState).every((keys) => !keys?.length)) {
      setSelection(defaultRoleSelection(roles, rawColumnNames));
    }
  }, [rawColumnNames.join(","), roles.map((role) => role.name).join(",")]);

  useLayoutEffect(() => {
    // With preprocessing, the first role the chain may transform defaults to
    // everything the chain leaves: the model is usually meant to use the
    // chain's whole result.
    if (!withPreprocessing || !structure) return;
    const first = roles.find((role) => role.transformable);
    if (first && (selection[first.name] || []).length === 0) {
      setSelection((prev) => ({ ...prev, [first.name]: finalOptions.allKeys }));
    }
  }, [structure]);

  const selectionKey = JSON.stringify(selection);
  const columnsAreValid =
    columnsReady && validated.key === selectionKey && validated.valid;

  const validateColumns = async (key) => {
    const current = () => latestValidation.current === key;
    try {
      // With preprocessing, the backend types every transformable role from
      // the chain's estimated structure, the same one these options come from.
      const validation = await validateColumnsRequest(
        newExp.task_name,
        dataset.id,
        selectionToRefs(selection),
        withPreprocessing ? steps : undefined,
      );
      if (!current()) return;
      setValidated({ key, valid: validation.dataset_status === "valid" });
      setValidationError(validation.error || null);
    } catch (error) {
      if (!current()) return;
      enqueueSnackbar(t("experiments:error.errorFetchingColumnsValidation"));
      console.error("Error validating columns:", error);
      setValidated({ key, valid: false });
    } finally {
      if (current()) setValidationPending(false);
    }
  };

  useLayoutEffect(() => {
    latestValidation.current = null;
    if (awaitingStructure) {
      // A pending check, not an invalid selection (see awaitingStructure).
      setValidationPending(true);
      return;
    }
    if (!columnsReady) {
      setValidationError(null);
      setValidationPending(false);
      return;
    }
    latestValidation.current = selectionKey;
    setValidationPending(true);
    validateColumns(selectionKey);
  }, [columnsReady, awaitingStructure, selectionKey]);

  useEffect(() => {
    if (columnsAreValid) {
      setNewExp({
        ...newExp,
        column_roles: selectionToRefs(selection),
        // The chain these picks were made for (see dropStaleGroupRefs).
        column_roles_steps: steps,
      });
      setNextEnabled(true);
    } else {
      setNextEnabled(false);
    }
  }, [columnsAreValid, selectionKey]);

  useEffect(() => {
    // Only needed to name the steps in the option labels, disambiguating two
    // of the same converter type (e.g. "Simple Imputer" / "Simple Imputer
    // (2)"), see buildStepDisplayNames.
    let cancelled = false;
    getComponentsRequest({ selectTypes: ["Converter"] })
      .then((data) => {
        if (cancelled) return;
        const byName = Object.fromEntries(
          (data || []).map((component) => [component.name, component]),
        );
        setConvertersMeta(byName);
      })
      .catch((error) =>
        console.error("Failed to fetch converter metadata:", error),
      );
    return () => {
      cancelled = true;
    };
  }, []);

  const describeCardinality = ({ min, max }) => {
    if (max === "n") {
      return min ? t("experiments:label.cardinalityAtLeast", { min }) : "n";
    }
    if (min === max) {
      return String(max);
    }
    return t("experiments:label.cardinalityBetween", { min, max });
  };

  const renderTypesAsChips = (typesList) => {
    if (!typesList || typesList.length === 0) {
      return <span>{t("common:any")}</span>;
    }
    return (
      <Box
        component="span"
        sx={{
          display: "inline-flex",
          gap: 1,
          flexWrap: "wrap",
          alignItems: "center",
        }}
      >
        {typesList.map((type, index) => (
          <React.Fragment key={type}>
            <Chip
              label={getColumnTypeLabel(type, t)}
              size="small"
              sx={{
                backgroundColor: getColorByColumnType(type),
                color: "#fff",
                fontWeight: 600,
                fontSize: "0.75rem",
                height: "22px",
              }}
            />
            {index < typesList.length - 1 && (
              <span style={{ margin: "0 4px" }}>{t("common:or")}</span>
            )}
          </React.Fragment>
        ))}
      </Box>
    );
  };

  const missing = (role) =>
    !awaitingStructure &&
    role.required &&
    (selection[role.name] || []).length === 0;

  return (
    <React.Fragment>
      {structureMissing && structureError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {t("models:structure.loadError")}
        </Alert>
      )}
      {roles.length > 0 && !validationPending && !structureMissing && (
        <Alert
          severity={columnsAreValid ? "success" : "error"}
          sx={{
            mb: 2,
            "& .MuiAlert-icon": { fontSize: 24 },
            bgcolor: (theme) =>
              `${theme.palette[columnsAreValid ? "success" : "error"].main}40`,
            border: (theme) =>
              `1px solid ${
                theme.palette[columnsAreValid ? "success" : "error"].main
              }`,
          }}
          data-tour="models-validation-alert"
        >
          <AlertTitle>
            {t(
              columnsAreValid
                ? "experiments:label.columnsValidRequirements"
                : "experiments:label.columnsInvalidRequirements",
              { taskName: taskDisplayName || newExp.task_name },
            )}
          </AlertTitle>
          <Grid container spacing={4}>
            {roles.map((role) => (
              <Grid size={{ xs: 12 }} key={role.name}>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 2,
                    flexWrap: "wrap",
                  }}
                >
                  <Trans
                    i18nKey="experiments:label.datasetRoleColumnRequirements"
                    values={{
                      role: role.label,
                      cardinality: describeCardinality(role),
                    }}
                  >
                    <span>The columns of the role must be of the types</span>
                    {renderTypesAsChips(role.types)}
                    <span>, and they should have a cardinality of </span>
                    <span>cardinality.</span>
                  </Trans>
                </Box>
              </Grid>
            ))}
            {!columnsAreValid && validationError && (
              <Grid size={{ xs: 12 }}>{validationError}</Grid>
            )}
          </Grid>
        </Alert>
      )}

      <Grid container spacing={2}>
        <RoleColumnSelectors
          roles={roles}
          selection={selection}
          onChange={(name, keys) =>
            setSelection((prev) => ({ ...prev, [name]: keys }))
          }
          optionsFor={(role) =>
            optionsForRole(role, baseOptionsFor(role), selection, roles)
          }
          columnTypes={columnTypesForSelector}
          optionLabels={optionLabels}
          errorFor={missing}
          helperTextFor={(role) => (missing(role) ? t("common:required") : "")}
          disabledFor={fixedRole}
          disabled={rawColumnNames.length === 0}
        />
      </Grid>
    </React.Fragment>
  );
}

SelectColumnsStep.propTypes = {
  newExp: PropTypes.object.isRequired,
  setNewExp: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
  dataset: PropTypes.object.isRequired,
  datasetInfo: PropTypes.object,
  datasetTypes: PropTypes.object,
  taskMetadata: PropTypes.object,
  taskDisplayName: PropTypes.string,
};

export default SelectColumnsStep;
