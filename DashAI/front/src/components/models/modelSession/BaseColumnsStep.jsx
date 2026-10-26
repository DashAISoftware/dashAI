import React, { useEffect, useLayoutEffect, useState } from "react";
import PropTypes from "prop-types";
import { Grid } from "@mui/material";
import { useTranslation } from "react-i18next";
import RoleColumnSelectors from "./RoleColumnSelectors";
import {
  defaultRoleSelection,
  optionsForRole,
  resolveSelection,
  selectionReady,
  shownRoles,
} from "./columnRoles";

/**
 * Step of the session wizard shown before preprocessing: give every role the
 * task declares its original dataset columns.
 *
 * For a role the preprocessing may transform these are candidates, the
 * columns the converter chain may work on; its final columns are picked from
 * what the chain leaves, in the last step. A protected role (e.g. a target)
 * gets its final columns here, and no converter can touch them. Nothing is
 * validated against the task: a candidate may be of a type the task rejects
 * (e.g. text) precisely because a converter will turn it into one it accepts.
 */
function BaseColumnsStep({
  newExp,
  setNewExp,
  setNextEnabled,
  datasetInfo,
  datasetTypes,
  taskMetadata,
}) {
  const { t } = useTranslation(["models", "common"]);
  const rawColumnNames = datasetInfo.column_names || [];
  const roles = shownRoles(taskMetadata);

  const [selectionState, setSelection] = useState(
    newExp.column_roles_stage1 || {},
  );

  // A column plays one role; a protected role keeps one two roles hold.
  const selection = resolveSelection(roles, selectionState);

  useLayoutEffect(() => {
    // The first time the dataset's columns and the task's roles are known.
    if (rawColumnNames.length === 0 || roles.length === 0) return;
    if (Object.values(selectionState).every((columns) => !columns?.length)) {
      setSelection(defaultRoleSelection(roles, rawColumnNames));
    }
  }, [rawColumnNames.join(","), roles.map((role) => role.name).join(",")]);

  const ready = roles.length > 0 && selectionReady(roles, selection);
  const selectionKey = JSON.stringify(selection);

  useEffect(() => {
    setNewExp((prev) => ({ ...prev, column_roles_stage1: selection }));
    setNextEnabled(ready);
  }, [selectionKey, ready]);

  const missing = (role) =>
    role.required && (selection[role.name] || []).length === 0;

  return (
    <Grid container spacing={2}>
      <RoleColumnSelectors
        roles={roles}
        selection={selection}
        onChange={(name, columns) =>
          setSelection((prev) => ({ ...prev, [name]: columns }))
        }
        optionsFor={(role) =>
          optionsForRole(role, rawColumnNames, selection, roles)
        }
        labelFor={(role) =>
          role.transformable
            ? t("models:label.candidatesForRole", { role: role.label })
            : role.label
        }
        columnTypes={datasetTypes}
        errorFor={missing}
        helperTextFor={(role) => (missing(role) ? t("common:required") : "")}
        disabled={rawColumnNames.length === 0}
      />
    </Grid>
  );
}

BaseColumnsStep.propTypes = {
  newExp: PropTypes.object.isRequired,
  setNewExp: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
  datasetInfo: PropTypes.object,
  datasetTypes: PropTypes.object,
  taskMetadata: PropTypes.object,
};

export default BaseColumnsStep;
