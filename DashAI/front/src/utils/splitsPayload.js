export const SPLIT_TYPES = {
  RANDOM: "random",
  MANUAL: "manual",
  PREDEFINED: "predefined",
  CV: "cv",
};

// Proportions describe a random split only. Manual and predefined splits carry
// the row indexes instead, and the backend splitter picks its index branch when
// no proportion is present, so sending both would be ambiguous.
const PROPORTION_KEYS = ["train", "test", "validation"];

const INDEX_MODES = [SPLIT_TYPES.MANUAL, SPLIT_TYPES.PREDEFINED];

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
