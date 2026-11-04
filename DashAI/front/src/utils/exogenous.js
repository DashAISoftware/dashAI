/**
 * What the run dialog says about a model and the session's exogenous
 * variables, as `{ key, values }` for i18n, or null when there is nothing to
 * say.
 *
 * The backend declares, per offered model, whether a run reads them and why
 * not (GET /model-session/{id}/exogenous-use), and names the parameter that
 * switches them off. This only crosses that declaration with the value the
 * form gives that parameter, as defaultRoleSelection crosses two
 * declarations: the front never decides whether a model uses them
 * (RECONCILING_FORECASTING §7.2, decision 7).
 */
export function exogenousNotice(declared, model, parameters) {
  const entry = declared?.models?.find((m) => m.model === model);
  if (!entry) return null;
  if (!entry.uses) return entry.reason;
  if (entry.switch && parameters?.[entry.switch] === false) {
    return { key: "exogenousSwitchedOff", values: { model } };
  }
  return null;
}
