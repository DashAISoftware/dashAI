// The final value of a metric: the number itself, or the last value of a
// per-step history.
function toFinalValue(value) {
  const resolved = Array.isArray(value)
    ? (value[value.length - 1]?.value ?? null)
    : value;
  const num = Number(resolved);
  return Number.isNaN(num) ? null : num;
}

/**
 * The final value of each metric a run reports on a split.
 *
 * A metric the run could not compute (MAPE on a zero) keeps its place with
 * no value and the reason the run gives, under {split}_metrics_unavailable.
 *
 * @param {object} run a run as the API returns it
 * @param {string} split "train", "validation", "test" or "full"
 * @returns {{name: string, value: number|null, reason: string|null}[]}
 */
export const metricSummary = (run, split) => {
  const values = Object.entries(run?.[`${split}_metrics`] ?? {})
    .map(([name, value]) => ({
      name,
      value: toFinalValue(value),
      reason: null,
    }))
    .filter(({ value }) => value !== null);
  const unavailable = Object.entries(
    run?.[`${split}_metrics_unavailable`] ?? {},
  ).map(([name, reason]) => ({ name, value: null, reason }));
  return [...values, ...unavailable];
};
