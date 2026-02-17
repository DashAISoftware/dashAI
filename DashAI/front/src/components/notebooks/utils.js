import { t } from "i18next";

export const formatScope = (scope) => {
  const cols = scope.columns?.length
    ? scope.columns.map((col) => col.columnName).join(", ")
    : t("common:all");
  const rows = scope.rows?.length ? scope.rows.join(", ") : t("common:all");
  return `${t("common:columns")}: ${cols} | ${t("common:rows")}: ${rows}`;
};
