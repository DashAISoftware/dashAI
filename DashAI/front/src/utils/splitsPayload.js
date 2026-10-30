export const SPLIT_TYPES = {
  RANDOM: "random",
  MANUAL: "manual",
  PREDEFINED: "predefined",
  CV: "cv",
};

/**
 * How an evaluation strategy divides the dataset.
 *
 * Read from the component's metadata rather than from its name. Comparing
 * names meant a new strategy rendered no split controls at all, since none of
 * the checks scattered through these screens matched it.
 */
export const STRATEGY_KINDS = {
  HOLDOUT: "holdout",
  CV: "cv",
  // Carves nothing: the model is fitted and scored once on every row, which is
  // the only evaluation a task without a target (clustering) offers.
  FULL: "full",
};

/**
 * Read the split shape a strategy component declares.
 *
 * @param {object} strategy an EvaluationStrategy component
 * @returns {string|null} "holdout", "cv", "full", or null when it declares none
 */
export const strategyKindOf = (strategy) => strategy?.metadata?.kind ?? null;

/**
 * Find the strategy component a session's stored strategy name refers to.
 *
 * @param {Array} strategies strategy components allowed for the task
 * @param {string} name the stored evaluation_strategy
 * @returns {object|null} the matching component
 */
export const findStrategy = (strategies, name) =>
  (strategies ?? []).find((strategy) => strategy?.name === name) ?? null;

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
 * The splitters a strategy takes, among those the task offers.
 *
 * The strategy declares the partitioning of the splitters it takes
 * (`splitter_partitioning`), and each splitter how it carves the dataset
 * (`partitioning`), so which splitter goes with which strategy is read from
 * both rather than inferred from a name or from the strategy's kind.
 *
 * @param {object} strategy the selected EvaluationStrategy component
 * @param {Array} splitters splitter components compatible with the task
 * @returns {Array} the splitters the strategy takes, in the order offered
 */
export const splittersOf = (strategy, splitters) => {
  const partitioning = strategy?.metadata?.splitter_partitioning;
  if (!partitioning) return [];
  return (splitters ?? []).filter(
    (splitter) => splitter?.metadata?.partitioning === partitioning,
  );
};

/**
 * The splitter a strategy starts a session on.
 *
 * The one it declares (`default_splitter`) when the task offers it, and the
 * first one it takes otherwise.
 *
 * @param {object} strategy the selected EvaluationStrategy component
 * @param {Array} splitters the splitters the strategy takes
 * @returns {object|null} the splitter to select by default
 */
export const defaultSplitterOf = (strategy, splitters) => {
  const options = splitters ?? [];
  const declared = strategy?.metadata?.default_splitter;
  return (
    options.find((splitter) => splitter?.name === declared) ??
    options[0] ??
    null
  );
};

/**
 * The metric lists of a new session, one per partition.
 *
 * Every metric the task offers is recorded on each partition that receives
 * rows, as the splitter's preview says; a partition without rows records none.
 *
 * @param {string[]|null} partitions the partitions with rows
 * @param {string[]} metricNames the metrics the task offers
 * @returns {{train: string[], validation: string[], test: string[]}}
 */
export const metricsByPartition = (partitions, metricNames) => {
  const has = (partition) => (partitions ?? []).includes(partition);
  return {
    train: has("train") ? metricNames : [],
    validation: has("validation") ? metricNames : [],
    test: has("test") ? metricNames : [],
  };
};
