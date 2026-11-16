import { useCallback, useEffect, useRef } from "react";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import { Box, TextField, MenuItem, Typography } from "@mui/material";
import ComponentDownloadControl, {
  useModelDownloadGate,
} from "../../../models/model/ComponentDownloadControl";
import DescriptionText from "../../../shared/DescriptionText";
import FormSchema from "../../../shared/FormSchema";
import FormSchemaContainer from "../../../shared/FormSchemaContainer";

/** Height cap for the parser parameter forms, so the dialog keeps one scroll. */
const PARAMETERS_MAX_HEIGHT = 320;

/**
 * @param {object} loader - A DataLoader component.
 * @returns {Array<string>} The extensions it can parse.
 */
function loaderExtensions(loader) {
  return loader?.metadata?.supported_extensions ?? [];
}

/**
 * @param {object} loader - A DataLoader component.
 * @returns {string} The label to show for it.
 */
function loaderLabel(loader) {
  return loader.display_name || loader.name;
}

/**
 * @param {object} loader - A DataLoader component.
 * @returns {string} Its description, wherever the backend put it.
 */
function loaderDescription(loader) {
  return loader?.description ?? loader?.schema?.description ?? "";
}

/**
 * Renders one parser's parameter form and reports its two gates upward.
 *
 * Living in its own component is what allows `useModelDownloadGate` to run per
 * loader: hooks cannot be called in a loop, and each parser has its own
 * download state and its own form.
 *
 * @param {object}   props
 * @param {object}   props.loader - The parser whose parameters are edited.
 * @param {object}   props.formRef - Ref that receives the formik object.
 * @param {Function} props.registerFormRef - Registers/unregisters the ref.
 * @param {Function} props.onFormErrorChange - Reports validation errors.
 * @param {Function} props.onDownloadGateChange - Reports a missing download.
 * @returns {JSX.Element}
 */
function LoaderParameters({
  loader,
  registerFormRef,
  onFormErrorChange,
  onDownloadGateChange,
  onValuesChange,
}) {
  const { t } = useTranslation("generative");
  const formRef = useRef(null);
  const { modelNotDownloaded } = useModelDownloadGate(loader, loader.name);
  const description = loaderDescription(loader);

  useEffect(() => {
    registerFormRef(loader.name, formRef);
    return () => registerFormRef(loader.name, null);
  }, [loader.name, registerFormRef]);

  useEffect(() => {
    onDownloadGateChange(loader.name, modelNotDownloaded);
    return () => onDownloadGateChange(loader.name, false);
  }, [loader.name, modelNotDownloaded, onDownloadGateChange]);

  const setError = useCallback(
    (hasError) => onFormErrorChange(loader.name, hasError),
    [loader.name, onFormErrorChange],
  );

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
        {loaderLabel(loader)}
      </Typography>
      <ComponentDownloadControl component={loader} />
      {description && (
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ whiteSpace: "pre-line" }}
        >
          <DescriptionText text={description} />
        </Typography>
      )}
      <Box
        sx={{
          maxHeight: PARAMETERS_MAX_HEIGHT,
          overflowY: "auto",
          overscrollBehavior: "contain",
        }}
      >
        <FormSchemaContainer>
          <FormSchema
            key={loader.name}
            autoSave
            model={loader.name}
            formSubmitRef={formRef}
            setError={setError}
            initialValues={{}}
            onValuesChange={() => onValuesChange?.(loader.name)}
            showBorder={false}
            hideButtons
          />
        </FormSchemaContainer>
      </Box>
      <Typography variant="caption" color="text.secondary">
        {t("generative:documentUpload.parserParametersHint")}
      </Typography>
    </Box>
  );
}

/**
 * One extension with the parsers that accept it.
 *
 * @param {object}   props
 * @param {string}   props.extension - The extension, or "" when there is none.
 * @param {Array}    props.entries - Files carrying that extension.
 * @param {Array}    props.loaders - Compatible parsers.
 * @param {string}   props.selectedName - Currently selected parser.
 * @param {Function} props.onSelect - Selects a parser for the extension.
 * @param {boolean}  props.disabled - Whether the upload already started.
 * @returns {JSX.Element}
 */
function ExtensionRow({
  extension,
  entries,
  loaders,
  selectedName,
  onSelect,
  disabled,
}) {
  const { t } = useTranslation(["generative"]);

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "flex-start",
        gap: 1.5,
        p: 1.5,
        border: 1,
        borderColor: "divider",
        borderRadius: 1,
      }}
    >
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Typography variant="body2" noWrap sx={{ fontWeight: 600 }}>
          {extension || t("generative:documentUpload.extensionNone")}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {t("generative:documentUpload.fileCount", {
            count: entries.length,
          })}
        </Typography>
      </Box>
      <TextField
        select
        size="small"
        label={t("generative:documentUpload.parserForExtension")}
        value={selectedName}
        onChange={(event) => onSelect(extension, event.target.value)}
        disabled={disabled}
        slotProps={{
          select: {
            "aria-label": t("generative:documentUpload.parserAriaLabel", {
              extension:
                extension || t("generative:documentUpload.extensionNone"),
            }),
          },
        }}
        sx={{ minWidth: 220 }}
      >
        {loaders.map((loader) => (
          <MenuItem key={loader.name} value={loader.name}>
            {loaderLabel(loader)}
          </MenuItem>
        ))}
      </TextField>
    </Box>
  );
}

/**
 * Lets the user pick one parser per extension and edit its parameters.
 *
 * Extensions sharing a parser share one form: the parser owns the parameters,
 * not the extension, so asking for them twice would be the same question.
 *
 * @param {object}   props
 * @param {Array<string>} props.extensions - Extensions present in the selection.
 * @param {object}   props.groupsByExtension - Extensions mapped to their files.
 * @param {Array}    props.loaders - Document loaders.
 * @param {object}   props.selectedByExtension - Extension to parser name.
 * @param {Function} props.onSelectLoader - Selects a parser for an extension.
 * @param {Function} props.registerFormRef - Registers a parser's form ref.
 * @param {Function} props.onFormErrorChange - Reports a form's error state.
 * @param {Function} props.onDownloadGateChange - Reports a missing download.
 * @param {boolean}  props.disabled - Whether the upload already started.
 * @returns {JSX.Element}
 */
export default function ExtensionParserConfig({
  extensions,
  groupsByExtension,
  loaders,
  selectedByExtension,
  onSelectLoader,
  registerFormRef,
  onFormErrorChange,
  onDownloadGateChange,
  onValuesChange,
  disabled,
}) {
  const { t } = useTranslation(["generative"]);

  const usedLoaders = [];
  for (const extension of extensions) {
    const loader = loaders.find(
      (candidate) => candidate.name === selectedByExtension[extension],
    );
    if (loader && !usedLoaders.some((used) => used.name === loader.name)) {
      usedLoaders.push(loader);
    }
  }

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 2,
        minWidth: 0,
      }}
    >
      <Typography
        variant="overline"
        color="text.secondary"
        sx={{ display: "block", lineHeight: 2 }}
      >
        {t("generative:documentUpload.parserPerExtension")}
      </Typography>

      {extensions.map((extension) => {
        const compatible = loaders.filter((loader) =>
          loaderExtensions(loader).includes(extension),
        );
        return (
          <ExtensionRow
            key={extension || "no-extension"}
            extension={extension}
            entries={groupsByExtension[extension]}
            loaders={compatible}
            selectedName={selectedByExtension[extension] ?? ""}
            onSelect={onSelectLoader}
            disabled={disabled}
          />
        );
      })}

      {usedLoaders.length > 0 && (
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            gap: 2,
            borderTop: 1,
            borderColor: "divider",
            pt: 2,
          }}
        >
          {usedLoaders.map((loader) => (
            <LoaderParameters
              key={loader.name}
              loader={loader}
              registerFormRef={registerFormRef}
              onFormErrorChange={onFormErrorChange}
              onDownloadGateChange={onDownloadGateChange}
              onValuesChange={onValuesChange}
            />
          ))}
        </Box>
      )}
    </Box>
  );
}

LoaderParameters.propTypes = {
  loader: PropTypes.object.isRequired,
  registerFormRef: PropTypes.func.isRequired,
  onFormErrorChange: PropTypes.func.isRequired,
  onDownloadGateChange: PropTypes.func.isRequired,
  onValuesChange: PropTypes.func,
};

ExtensionRow.propTypes = {
  extension: PropTypes.string.isRequired,
  entries: PropTypes.arrayOf(PropTypes.object).isRequired,
  loaders: PropTypes.arrayOf(PropTypes.object).isRequired,
  selectedName: PropTypes.string,
  onSelect: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
};

ExtensionParserConfig.propTypes = {
  extensions: PropTypes.arrayOf(PropTypes.string).isRequired,
  groupsByExtension: PropTypes.object.isRequired,
  loaders: PropTypes.arrayOf(PropTypes.object).isRequired,
  selectedByExtension: PropTypes.object.isRequired,
  onSelectLoader: PropTypes.func.isRequired,
  registerFormRef: PropTypes.func.isRequired,
  onFormErrorChange: PropTypes.func.isRequired,
  onDownloadGateChange: PropTypes.func.isRequired,
  onValuesChange: PropTypes.func,
  disabled: PropTypes.bool,
};
