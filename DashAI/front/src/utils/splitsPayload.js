export const SPLIT_TYPES = {
  RANDOM: "random",
  MANUAL: "manual",
  PREDEFINED: "predefined",
  CV: "cv",
};

export const HOLDOUT_STRATEGY = "HoldoutEvaluationStrategy";
export const CV_STRATEGY = "CrossValidationEvaluationStrategy";

// Proportions describe a random split only. Manual and predefined splits carry
// the row indexes instead, and the backend splitter picks its index branch when
// no proportion is present, so sending both would be ambiguous.
const PROPORTION_KEYS = ["train", "test", "validation"];

const INDEX_MODES = [SPLIT_TYPES.MANUAL, SPLIT_TYPES.PREDEFINED];

const PARTITION_INDEX_KEYS = {
  train: "train_indexes",
  validation: "val_indexes",
  test: "test_indexes",
};

/**
 * Build the splits payload stored on a model session.
 *
 * The selected splitter's schema parameters stay at the top level, next to the
 * three meta keys the schemas do not own: splitter_name, splitType and
 * splitted_indexes. Keeping the schema keys verbatim is what stops the payload
 * and the splitter from drifting apart.
 *
 * @param {string} splitterName registry name of the selected splitter
 * @param {string} splitType one of SPLIT_TYPES
 * @param {object} params values submitted by the schema generated form
 * @param {object} indexes row indexes per partition, for the index modes
 * @returns {object} the payload to serialize into the model session splits
 */
export const buildSplitsPayload = ({
  splitterName,
  splitType,
  params = {},
  indexes = null,
}) => {
  const isIndexMode = INDEX_MODES.includes(splitType);

  const payload = { splitter_name: splitterName, splitType };

  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value === undefined) return;
    if (isIndexMode && PROPORTION_KEYS.includes(key)) return;
    payload[key] = value;
  });

  if (isIndexMode) {
    payload.splitted_indexes = {
      train_indexes: indexes?.train ?? [],
      test_indexes: indexes?.test ?? [],
      val_indexes: indexes?.validation ?? [],
    };
  }

  return payload;
};

/**
 * Resolve the registry name of the splitter a session configuration uses.
 *
 * Holdout has a single splitter; cross-validation picks one from the registry.
 *
 * @param {string} evaluationStrategy the selected evaluation strategy
 * @param {object} cvType the splitter component selected for cross-validation
 * @returns {string|null} the splitter name, or null when none is resolved yet
 */
export const resolveSplitterName = (evaluationStrategy, cvType) => {
  if (evaluationStrategy === HOLDOUT_STRATEGY) return "HoldoutSplitter";
  if (evaluationStrategy === CV_STRATEGY) return cvType?.name ?? null;
  return null;
};

/**
 * Report whether a splits payload gives a partition any rows.
 *
 * Cross-validation splits every fold into train and validation, so those two
 * always receive rows; it only fills a test partition when the session reserved
 * rows the folds never see. Index modes carry row indexes, random splits carry
 * proportions, and payloads written before the splits followed the splitter
 * schema carry the indexes under the partition names.
 *
 * @param {object} splits a splits payload
 * @param {string} partition one of "train", "validation", "test"
 * @returns {boolean} true when the partition receives rows
 */
export const hasPartition = (splits, partition) => {
  if (!splits) return false;
  if (splits.splitType === SPLIT_TYPES.CV) {
    // Sessions written while the reserved proportion was still called
    // "holdout" carry that key instead, the same fallback the backend
    // normalizer applies.
    if (partition === "test")
      return Number(splits.test_size ?? splits.holdout ?? 0) > 0;
    return true;
  }

  const indexes = splits.splitted_indexes;
  if (indexes) {
    return (indexes[PARTITION_INDEX_KEYS[partition]] ?? []).length > 0;
  }

  const value = splits[partition];
  if (Array.isArray(value)) return value.length > 0;
  return typeof value === "number" && value !== 0;
};
