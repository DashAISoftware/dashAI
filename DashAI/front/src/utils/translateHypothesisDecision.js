/**
 * Generate hypothesis test interpretation message based on test results and language
 * @param {boolean} significant - Whether the result is significant
 * @param {number} pValue - The p-value from the test
 * @param {number} alpha - The significance level
 * @param {Function} t - i18next translation function
 * @returns {string} Localized hypothesis decision message
 */
export const getHypothesisDecisionMessage = (significant, pValue, alpha, t) => {
  if (!t) return "";

  const decision = significant
    ? t("models:message.hypothesis_reject")
    : t("models:message.hypothesis_failToReject");

  return t("models:message.hypothesisDecision", {
    decision,
    pValue,
    alpha,
  });
};
