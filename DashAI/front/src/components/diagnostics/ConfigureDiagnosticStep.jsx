import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { Box, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";

import FormSchema from "../shared/FormSchema";
import FormSchemaLayout from "../shared/FormSchemaLayout";

/**
 * Parameter step of the diagnostic creator, rendered from the component's own
 * schema the same way every other configurable object in DashAI is configured.
 *
 * Only reached for diagnostics that actually take parameters; the creator
 * drops this step entirely for the ones that do not.
 */
export default function ConfigureDiagnosticStep({
  newDiagnostic,
  setNewDiagnostic,
  setNextEnabled,
  formSubmitRef,
  defaultValues,
}) {
  const { t } = useTranslation(["diagnostics"]);
  const [error, setError] = useState(false);

  const isParamsEmpty =
    !newDiagnostic.parameters ||
    Object.keys(newDiagnostic.parameters).length === 0;

  useEffect(() => {
    if (isParamsEmpty && Boolean(defaultValues)) {
      setNewDiagnostic((prev) => ({ ...prev, parameters: defaultValues }));
    }
  }, [isParamsEmpty, defaultValues, setNewDiagnostic]);

  useEffect(() => {
    setNextEnabled(!error);
  }, [error, setNextEnabled]);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <Typography variant="subtitle2">
        {t("diagnostics:label.parameters")}
      </Typography>
      <FormSchemaLayout>
        <FormSchema
          autoSave
          model={newDiagnostic.diagnostic_name}
          onFormSubmit={(values) =>
            setNewDiagnostic((prev) => ({ ...prev, parameters: values }))
          }
          setError={setError}
          formSubmitRef={formSubmitRef}
        />
      </FormSchemaLayout>
    </Box>
  );
}

ConfigureDiagnosticStep.propTypes = {
  newDiagnostic: PropTypes.shape({
    diagnostic_name: PropTypes.string,
    parameters: PropTypes.object,
  }).isRequired,
  setNewDiagnostic: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
  formSubmitRef: PropTypes.shape({ current: PropTypes.any }).isRequired,
  defaultValues: PropTypes.object,
};
