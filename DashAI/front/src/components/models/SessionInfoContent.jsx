import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { Box, Typography, Chip } from "@mui/material";
import { useTranslation } from "react-i18next";
import { formatDate } from "../../utils";
import { getComponents } from "../../api/component";
import ParamInfoList, { ParamInfoBox } from "./ParamInfoBox";
import {
  buildStepDisplayNames,
  labelForRef,
} from "./modelSession/sessionColumnRefs";
import { useSessionRoleColumns } from "../../hooks/useTaskMetadata";

// The keys of a splits payload that are not the splitter's parameters.
const SPLITS_META_KEYS = ["splitter_name", "splitType", "splitted_indexes"];

const SPLIT_TYPE_LABEL_KEYS = {
  random: "experiments:label.random",
  manual: "experiments:label.manual",
  predefined: "experiments:label.predefined",
  cv: "experiments:label.crossValidation",
};

/**
 * Shared body for a session's info: task, description, metadata (id,
 * dataset, dates) and the configuration it was created with (the columns of
 * each role, split setup). Used both by InfoSessionModal (a dialog) and the
 * model detail view's right sidebar (RunInfoSidebar's "Session" tab).
 */
export default function SessionInfoContent({
  session,
  datasets = [],
  tasks = [],
}) {
  const { t } = useTranslation(["common", "experiments", "models"]);
  // One row per role, as the task labels its roles: a task's roles need not
  // be inputs and outputs.
  const roleColumns = useSessionRoleColumns(session);
  const [convertersMeta, setConvertersMeta] = useState({});
  const [splitterComponent, setSplitterComponent] = useState(null);

  useEffect(() => {
    let cancelled = false;
    getComponents({ selectTypes: ["Converter"] })
      .then((data) => {
        if (cancelled) return;
        setConvertersMeta(
          Object.fromEntries((data || []).map((c) => [c.name, c])),
        );
      })
      .catch((error) =>
        console.error("Failed to fetch converter metadata:", error),
      );
    return () => {
      cancelled = true;
    };
  }, []);

  let splits = null;
  try {
    splits =
      typeof session?.splits === "string"
        ? JSON.parse(session.splits)
        : session?.splits;
  } catch {
    splits = null;
  }
  // A strategy without a form of its own stores its splitter's parameters
  // alone, with no split type; its schema names them.
  const genericSplitter =
    splits && !splits.splitType ? (splits.splitter_name ?? null) : null;

  useEffect(() => {
    if (!genericSplitter) return undefined;
    let cancelled = false;
    getComponents({ model: genericSplitter })
      .then((component) => {
        if (!cancelled) setSplitterComponent(component);
      })
      .catch((error) =>
        console.error("Failed to fetch the splitter metadata:", error),
      );
    return () => {
      cancelled = true;
    };
  }, [genericSplitter]);

  if (!session) return null;

  const preprocessingSteps = session.preprocessing?.steps || [];
  const stepDisplayNames = buildStepDisplayNames(
    preprocessingSteps,
    convertersMeta,
  );

  const getDatasetName = () => {
    if (!session.dataset_id || !datasets.length) return t("common:unknown");
    const dataset = datasets.find((d) => d.id === session.dataset_id);
    return dataset ? dataset.name : t("common:datasetNotFound");
  };

  const getTaskDisplayName = () => {
    if (!session.task_name) return t("common:unknown");
    const task = tasks.find((tk) => tk.name === session.task_name);
    return (
      task?.metadata?.display_name ||
      session.task_name
        .replace("Task", "")
        .replace(/([A-Z])/g, " $1")
        .trim()
    );
  };

  const metadataRows = [
    [t("common:id"), session.id],
    [t("common:associatedDataset"), getDatasetName()],
    [t("common:createdAt"), formatDate(session.created)],
    [t("common:lastModified"), formatDate(session.last_modified)],
  ];

  const yesNo = (value) => t(value ? "common:yes" : "common:no");

  const configRows = roleColumns.map((role) => [
    role.label,
    role.columns.join(", "),
  ]);

  if (genericSplitter) {
    const properties = splitterComponent?.schema?.properties ?? {};
    configRows.push([
      t("experiments:label.splitter"),
      splitterComponent?.display_name ?? genericSplitter,
    ]);
    Object.entries(splits)
      .filter(([key]) => !SPLITS_META_KEYS.includes(key))
      .forEach(([key, value]) => {
        configRows.push([
          properties[key]?.title ?? key,
          typeof value === "boolean" ? yesNo(value) : value,
        ]);
      });
  } else if (splits?.splitType) {
    configRows.push([
      t("experiments:label.splitType"),
      t(SPLIT_TYPE_LABEL_KEYS[splits.splitType] || splits.splitType),
    ]);

    // Sessions created before the splits payload followed the splitter schema
    // stored the seed as "seed" and the manual indexes under the partition
    // names, so both shapes are read here.
    const seed = splits.random_state ?? splits.seed;

    if (splits.splitType === "random") {
      configRows.push(
        [t("common:train"), splits.train],
        [t("common:validation"), splits.validation],
        [t("common:test"), splits.test],
        [t("experiments:label.shuffle"), yesNo(splits.shuffle)],
        [t("experiments:label.stratify"), yesNo(splits.stratify)],
        [t("experiments:label.seed"), seed],
      );
    } else if (splits.splitType === "cv") {
      if (splits.n_splits !== undefined) {
        configRows.push([t("experiments:label.numFolds"), splits.n_splits]);
      }
      if (splits.n_repeats !== undefined) {
        configRows.push([t("experiments:label.numRepeats"), splits.n_repeats]);
      }
      if (splits.group_column) {
        configRows.push([
          t("experiments:label.groupColumn"),
          splits.group_column,
        ]);
      }
      configRows.push([t("experiments:label.seed"), seed]);
    } else {
      const indexes = splits.splitted_indexes || {};
      configRows.push(
        [
          t("common:train"),
          (indexes.train_indexes ?? splits.train ?? []).length,
        ],
        [
          t("common:validation"),
          (indexes.val_indexes ?? splits.validation ?? []).length,
        ],
        [t("common:test"), (indexes.test_indexes ?? splits.test ?? []).length],
      );
    }
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <Box>
        <Chip
          label={getTaskDisplayName()}
          color="primary"
          size="small"
          sx={{ mb: 2 }}
        />
        {session.description && session.description.trim() && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 2 }}>
              {t("common:description")}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {session.description}
            </Typography>
          </Box>
        )}
      </Box>

      <Box>
        <Typography variant="subtitle2" gutterBottom>
          {t("models:label.sessionConfiguration")}
        </Typography>
        <ParamInfoList rows={configRows} />
      </Box>

      {preprocessingSteps.length > 0 && (
        <Box>
          <Typography variant="subtitle2" gutterBottom>
            {t("models:label.appliedConverters")}
          </Typography>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {preprocessingSteps.map((step, index) => (
              <ParamInfoBox
                key={`${step.converter}-${index}`}
                label={stepDisplayNames[index]}
                value={(step.scope || [])
                  .map((ref) => labelForRef(ref, stepDisplayNames, t))
                  .join(", ")}
              />
            ))}
          </Box>
        </Box>
      )}

      <Box>
        <Typography variant="subtitle2" gutterBottom>
          {t("common:metadata")}
        </Typography>
        <ParamInfoList rows={metadataRows} />
      </Box>
    </Box>
  );
}

SessionInfoContent.propTypes = {
  session: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    dataset_id: PropTypes.number,
    task_name: PropTypes.string,
    task_name: PropTypes.string,
    column_roles: PropTypes.object,
    splits: PropTypes.oneOfType([PropTypes.string, PropTypes.object]),
    created: PropTypes.string,
    last_modified: PropTypes.string,
    description: PropTypes.string,
    preprocessing: PropTypes.shape({
      steps: PropTypes.arrayOf(
        PropTypes.shape({
          converter: PropTypes.string,
          scope: PropTypes.array,
        }),
      ),
    }),
  }),
  datasets: PropTypes.array,
  tasks: PropTypes.array,
};
