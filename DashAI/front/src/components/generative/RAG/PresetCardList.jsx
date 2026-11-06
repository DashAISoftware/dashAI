import PropTypes from "prop-types";
import { Box, ButtonBase, Stack, Typography } from "@mui/material";
import CheckIcon from "@mui/icons-material/Check";

/**
 * A vertical list of selectable preset cards.
 *
 * Wears the same card treatment as `ComponentSelector` -- a border that turns
 * primary when active, a tick in the corner -- so a preset reads like the
 * component choices elsewhere in the module. It is a `ButtonBase`, not a
 * `Paper` with a click handler: a preset is a choice, and a choice has to be
 * reachable and operable from the keyboard.
 *
 * @param {object}   props
 * @param {Array}    props.presets - Presets, each `{key, display_name,
 *   description, component, params}`.
 * @param {string}   [props.activeKey] - The preset the draft currently matches,
 *   or null when the configuration is custom.
 * @param {Function} props.onSelect - Called with the chosen preset.
 * @returns {JSX.Element} The card list.
 */
export default function PresetCardList({ presets, activeKey, onSelect }) {
  return (
    <Stack spacing={1}>
      {presets.map((preset) => {
        const isSelected = activeKey === preset.key;
        return (
          <ButtonBase
            key={preset.key}
            onClick={() => onSelect(preset)}
            aria-pressed={isSelected}
            sx={{
              display: "block",
              width: "100%",
              p: 2,
              textAlign: "left",
              cursor: "pointer",
              border: 1,
              borderColor: isSelected ? "primary.main" : "divider",
              borderRadius: 1,
              bgcolor: isSelected ? "action.selected" : "background.paper",
              transition:
                "background-color 150ms ease-out, border-color 150ms ease-out",
              "&:focus-visible": {
                outline: "2px solid",
                outlineColor: "primary.main",
                outlineOffset: 2,
              },
              "@media (hover: hover)": {
                "&:hover": {
                  borderColor: isSelected ? "primary.main" : "secondary.main",
                },
              },
            }}
          >
            <Stack direction="row" alignItems="flex-start" spacing={1}>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography variant="subtitle2">
                  {preset.display_name}
                </Typography>
                {preset.description && (
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{
                      display: "-webkit-box",
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: "vertical",
                      overflow: "hidden",
                      mt: 0.5,
                    }}
                  >
                    {preset.description}
                  </Typography>
                )}
              </Box>
              {isSelected && (
                <CheckIcon
                  fontSize="small"
                  color="primary"
                  sx={{ mt: 0.25, flexShrink: 0 }}
                />
              )}
            </Stack>
          </ButtonBase>
        );
      })}
    </Stack>
  );
}

PresetCardList.propTypes = {
  presets: PropTypes.array.isRequired,
  activeKey: PropTypes.string,
  onSelect: PropTypes.func.isRequired,
};
