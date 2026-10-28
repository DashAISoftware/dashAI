import React from "react";
import PropTypes from "prop-types";
import { Alert, AlertTitle, Box, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";

/**
 * The records of several predictions as one list, for a view that shows them
 * together (the manual predictions, one row each). Records of the same
 * column treated by the same encoder are joined; `count` keeps the largest,
 * since a record may only list a sample of its values.
 */
export function mergeUnseen(predictions) {
  const merged = new Map();
  (predictions || []).forEach((prediction) => {
    (prediction.unseen_categories || []).forEach((record) => {
      const key = `${record.source}/${record.column}`;
      const current = merged.get(key);
      if (!current) {
        merged.set(key, { ...record, values: [...record.values] });
        return;
      }
      const values = [...new Set([...current.values, ...record.values])].sort();
      current.values = values;
      current.count = Math.max(current.count, record.count, values.length);
    });
  });
  return [...merged.values()];
}

/**
 * Warns that a prediction met categories training never saw.
 *
 * The encoders treat such a category instead of refusing it (a row of zeros
 * for one-hot, -1 for label and ordinal), so the prediction still runs, but
 * those rows are predicted from something the model never learnt. Each record
 * names the column, what treated it (a session step or the model) and a
 * sample of the values; `count` says how many there were in all.
 */
export default function UnseenCategoriesAlert({ unseen }) {
  const { t } = useTranslation(["prediction"]);
  if (!unseen?.length) return null;

  return (
    <Alert severity="warning" sx={{ mb: 2 }}>
      <AlertTitle>{t("prediction:unseen.title")}</AlertTitle>
      <Typography variant="body2" sx={{ mb: 1 }}>
        {t("prediction:unseen.description")}
      </Typography>
      <Box component="ul" sx={{ m: 0, pl: 2 }}>
        {unseen.map((record) => {
          const rest = record.count - record.values.length;
          const values =
            rest > 0
              ? `${record.values.join(", ")} ${t("prediction:unseen.more", {
                  count: rest,
                })}`
              : record.values.join(", ");
          return (
            <li key={`${record.source}/${record.column}`}>
              <Typography variant="body2">
                {t("prediction:unseen.line", {
                  column: record.column,
                  source: record.source,
                  values,
                  interpolation: { escapeValue: false },
                })}
              </Typography>
            </li>
          );
        })}
      </Box>
    </Alert>
  );
}

UnseenCategoriesAlert.propTypes = {
  unseen: PropTypes.arrayOf(
    PropTypes.shape({
      source: PropTypes.string.isRequired,
      column: PropTypes.string.isRequired,
      values: PropTypes.arrayOf(PropTypes.string).isRequired,
      count: PropTypes.number.isRequired,
    }),
  ),
};
