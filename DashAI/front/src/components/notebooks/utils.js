export const formatScope = (scope) => {
  const cols = scope.columns?.length ? scope.columns.join(", ") : "All";
  const rows = scope.rows?.length ? scope.rows.join(", ") : "All";
  return `Columns: ${cols} | Rows: ${rows}`;
};
