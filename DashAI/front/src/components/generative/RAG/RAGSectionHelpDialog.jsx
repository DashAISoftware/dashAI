import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import { Alert, Box, Button, Divider, Stack, Typography } from "@mui/material";
import RAGAdvancedDialog from "../../../pages/generative/RAGSession/advanced/RAGAdvancedDialog";

/**
 * Translation root of every help string. Kept as one constant because the
 * parameter lookups below interpolate a dynamic name into the same prefix.
 */
const HELP_BASE = "generative:rag.help";

/**
 * Explain one parameter, preferring the curated help over the schema text.
 *
 * The backend already localizes each schema description, but it is written for
 * whoever builds the pipeline, not for whoever configures a session. The help
 * bundle carries a short, task-oriented sentence for the parameters that
 * matter; the schema description is the fallback for the rest and the explicit
 * "no description" note is the last resort.
 *
 * @param {{name: string, description?: string}} param - The parameter entry.
 * @param {Function} t - The i18next translator.
 * @returns {string} The explanation to render.
 */
function describeParam(param, t) {
  return (
    t(`${HELP_BASE}.parameterHelp.${param.name}`, { defaultValue: "" }) ||
    param.description ||
    t(`${HELP_BASE}.noDescription`)
  );
}

/**
 * The parameters worth explaining first, per pipeline stage.
 *
 * This is presentation order, not a filter: a name listed here is shown ahead
 * of the rest only when the configured component actually exposes it. Names a
 * component does not have are never invented, so the modal can talk about a
 * technique the current retriever or transformer does not implement without
 * claiming parameters the user cannot find in the form.
 */
const KEY_PARAMETERS = {
  chunking_model: ["chunk_size", "chunk_overlap"],
  query_transformation: [
    "history_window",
    "n_queries",
    "max_subqueries",
    "prompt",
    "llm_model",
  ],
  retriever_model: ["top_k", "enable_retrieve_then_expand", "expand_window"],
  generation_model: ["max_tokens", "temperature", "context_window", "device"],
  prompt: ["template", "language"],
};

/**
 * Turn the section's real parameters into the ordered list the dialog shows.
 *
 * Only what `section.params` contains is displayed: the curated key parameters
 * that exist come first, then every remaining parameter in the order the
 * backend sent it. A component with no parameters -- an optional stage that is
 * off, for instance -- therefore yields an empty list and the dialog shows the
 * `noParameters` note instead of a fabricated one.
 *
 * @param {object} section - The localized section from `configuration`.
 * @param {string} sectionKey - The pipeline key, e.g. `retriever_model`.
 * @returns {Array<{name: string, label: string, description?: string}>} The
 *   parameter entries, first occurrence of each name only.
 */
function buildParamEntries(section, sectionKey) {
  const params = Array.isArray(section.params) ? section.params : [];
  const byName = new Map();
  for (const param of params) {
    if (param && param.name && !byName.has(param.name)) {
      byName.set(param.name, param);
    }
  }

  const order = KEY_PARAMETERS[sectionKey] || [];
  const entries = order
    .filter((name) => byName.has(name))
    .map((name) => byName.get(name));
  const seen = new Set(entries.map((param) => param.name));

  for (const param of params) {
    if (!param || !param.name || seen.has(param.name)) continue;
    entries.push(param);
    seen.add(param.name);
  }

  return entries;
}

/**
 * The modal behind the question mark next to every pipeline section.
 *
 * The panel shows what a section is set to but not what the stage does, so a
 * user changing a chunk size or a top-k has no way to know what to expect.
 * This dialog answers the three questions that configuration raises: what the
 * stage and its selected component do, what a good starting point looks like,
 * and what the parameters it exposes actually change.
 *
 * @param {object}   props
 * @param {boolean}  props.open - Whether the dialog is open.
 * @param {Function} props.onClose - Called when the dialog asks to close.
 * @param {string?}  props.sectionKey - The pipeline key being explained.
 * @param {object?}  props.section - The localized section from the panel.
 * @param {boolean}  [props.dirty] - Whether the section has unsaved edits,
 *   in which case the explanation describes the saved configuration.
 * @returns {JSX.Element|null} The dialog, or nothing while it is closed.
 */
export default function RAGSectionHelpDialog({
  open,
  onClose,
  sectionKey,
  section,
  dirty = false,
}) {
  const { t } = useTranslation(["generative"]);

  if (!open || !section || !sectionKey) return null;

  const base = `${HELP_BASE}.sections.${sectionKey}`;
  const what = t(`${base}.what`, { defaultValue: "" });
  const recommendations = t(`${base}.recommendations`, {
    returnObjects: true,
  });
  const recommendationItems = Array.isArray(recommendations)
    ? recommendations
    : [];
  const params = buildParamEntries(section, sectionKey);
  const stageDisabled = section.enabled === false;

  return (
    <RAGAdvancedDialog
      open={open}
      onClose={onClose}
      title={t(`${HELP_BASE}.title`, { section: section.section_name })}
      maxWidth={false}
      minHeight={0}
      paperSx={{
        width: { xs: "90vw", sm: "85vw", md: "60vw" },
        maxWidth: 1100,
      }}
      actions={
        <Button variant="contained" size="small" onClick={onClose}>
          {t(`${HELP_BASE}.dismiss`)}
        </Button>
      }
    >
      <Stack spacing={3}>
        {dirty && <Alert severity="info">{t(`${HELP_BASE}.unsaved`)}</Alert>}

        {(what || stageDisabled) && (
          <Box>
            {what && (
              <>
                <Typography
                  component="h3"
                  variant="subtitle2"
                  sx={{ fontWeight: 600, mb: 1 }}
                >
                  {t(`${HELP_BASE}.howItWorks`)}
                </Typography>
                <Typography variant="body2">{what}</Typography>
              </>
            )}
            {stageDisabled && (
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ mt: what ? 1 : 0 }}
              >
                {t(`${base}.disabled`)}
              </Typography>
            )}
          </Box>
        )}

        {recommendationItems.length > 0 && (
          <Box>
            <Typography
              component="h3"
              variant="subtitle2"
              sx={{ fontWeight: 600, mb: 1 }}
            >
              {t(`${HELP_BASE}.recommendations`)}
            </Typography>
            <Stack component="ul" spacing={0.75} sx={{ m: 0, pl: 2.5 }}>
              {recommendationItems.map((item, index) => (
                <Typography component="li" variant="body2" key={index}>
                  {item}
                </Typography>
              ))}
            </Stack>
          </Box>
        )}

        {section.display_name && (
          <Box>
            <Typography variant="overline" color="text.secondary">
              {t(`${HELP_BASE}.component`)}
            </Typography>
            <Typography
              component="h3"
              variant="subtitle1"
              sx={{ fontWeight: 600 }}
            >
              {section.display_name}
            </Typography>
            {section.description && (
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ mt: 0.5 }}
              >
                {section.description}
              </Typography>
            )}
          </Box>
        )}

        <Box>
          <Typography
            component="h3"
            variant="subtitle2"
            sx={{ fontWeight: 600, mb: 1 }}
          >
            {t(`${HELP_BASE}.parameters`)}
          </Typography>
          {params.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              {t(`${HELP_BASE}.noParameters`)}
            </Typography>
          ) : (
            <Stack divider={<Divider flexItem />} spacing={1.5}>
              {params.map((param) => (
                <Box key={param.name}>
                  <Typography
                    component="p"
                    variant="body2"
                    sx={{ fontWeight: 600 }}
                  >
                    {param.label}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {describeParam(param, t)}
                  </Typography>
                </Box>
              ))}
            </Stack>
          )}
        </Box>
      </Stack>
    </RAGAdvancedDialog>
  );
}

RAGSectionHelpDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  sectionKey: PropTypes.string,
  section: PropTypes.shape({
    section_name: PropTypes.string,
    display_name: PropTypes.string,
    description: PropTypes.string,
    enabled: PropTypes.bool,
    params: PropTypes.arrayOf(
      PropTypes.shape({
        name: PropTypes.string,
        label: PropTypes.string,
        description: PropTypes.string,
      }),
    ),
  }),
  dirty: PropTypes.bool,
};
