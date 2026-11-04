import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { Alert } from "@mui/material";
import { useTranslation } from "react-i18next";
import { getExogenousUse } from "../../api/modelSession";
import { exogenousNotice } from "../../utils/exogenous";

/**
 * Say, before training, that a run of this model will not read the
 * session's exogenous variables, and why. The reason is the backend's
 * declaration; the form's value of the switch it names only says whether it
 * is off right now.
 */
export default function ExogenousUseNotice({ sessionId, model, parameters }) {
  const { t } = useTranslation(["models"]);
  const [declared, setDeclared] = useState(null);

  useEffect(() => {
    let cancelled = false;
    if (sessionId == null) return undefined;
    getExogenousUse(sessionId)
      .then((answer) => {
        if (!cancelled) setDeclared(answer);
      })
      .catch((error) =>
        console.error("Error fetching the exogenous use:", error),
      );
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const notice = exogenousNotice(declared, model, parameters);
  if (!notice) return null;
  return (
    <Alert severity="info" sx={{ mb: 4 }}>
      {t(`models:exogenous.reason.${notice.key}`, notice.values)}
    </Alert>
  );
}

ExogenousUseNotice.propTypes = {
  sessionId: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  model: PropTypes.string.isRequired,
  parameters: PropTypes.object,
};
