import { Button, ButtonGroup } from "@mui/material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";

function FormSchemaButtonGroup({
  onCancel,
  onFormSubmit,
  autoSave,
  formik,
  error,
  saveButtonText,
  backButtonText,
  dataTour,
}) {
  const { t } = useTranslation(["common", "datasets"]);
  const finalSaveText = saveButtonText ?? t("common:save");
  const finalBackText = backButtonText ?? t("common:back");

  const isCreateExplorer =
    saveButtonText === t("datasets:button.createExplorer");
  const isCreateConverter =
    saveButtonText === t("datasets:button.createConverter");
  const finalDataTour =
    dataTour ||
    (isCreateExplorer
      ? "create-explorer-button"
      : isCreateConverter
        ? "create-converter-button"
        : undefined);

  return (
    <ButtonGroup
      size="large"
      sx={{
        justifyContent: "flex-end",
        width: "100%",
        display: "flex",
        mt: 3,
      }}
    >
      {onCancel && (
        <Button variant="outlined" onClick={onCancel}>
          {finalBackText}
        </Button>
      )}
      {!autoSave && (
        <Button
          variant="contained"
          onClick={() => onFormSubmit(formik?.values)}
          disabled={Object.keys(formik?.errors ?? {}).length > 0 || error}
          data-tour={finalDataTour}
        >
          {finalSaveText}
        </Button>
      )}
    </ButtonGroup>
  );
}

FormSchemaButtonGroup.propTypes = {
  onCancel: PropTypes.func,
  onFormSubmit: PropTypes.func,
  autoSave: PropTypes.bool,
  formik: PropTypes.object,
  error: PropTypes.bool,
  saveButtonText: PropTypes.string,
  backButtonText: PropTypes.string,
  dataTour: PropTypes.string,
};

export default FormSchemaButtonGroup;
