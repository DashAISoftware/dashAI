import { useLayoutEffect, useRef, useState } from "react";
import { Button, ButtonGroup } from "@mui/material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";

const DEFAULT_MIN_WIDTH = 96;

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

  const cancelRef = useRef(null);
  const submitRef = useRef(null);
  const [btnWidth, setBtnWidth] = useState(null);

  const hasBothButtons = !!onCancel && !autoSave;

  useLayoutEffect(() => {
    if (!hasBothButtons) return;
    const w = Math.max(
      cancelRef.current?.scrollWidth ?? 0,
      submitRef.current?.scrollWidth ?? 0,
      DEFAULT_MIN_WIDTH,
    );
    setBtnWidth(w);
  }, [hasBothButtons, finalSaveText, finalBackText]);

  const btnStyle =
    btnWidth !== null
      ? {
          minWidth: `${btnWidth}px`,
          width: `${btnWidth}px`,
          whiteSpace: "nowrap",
        }
      : hasBothButtons
        ? { whiteSpace: "nowrap" }
        : { minWidth: `${DEFAULT_MIN_WIDTH}px`, whiteSpace: "nowrap" };

  return (
    <ButtonGroup size="large" sx={{ justifyContent: "flex-end" }}>
      {onCancel && (
        <Button
          ref={cancelRef}
          variant="outlined"
          onClick={onCancel}
          style={btnStyle}
        >
          {finalBackText}
        </Button>
      )}
      {!autoSave && (
        <Button
          ref={submitRef}
          variant="contained"
          onClick={onFormSubmit}
          disabled={Object.keys(formik?.errors ?? {}).length > 0 || error}
          data-tour={finalDataTour}
          style={btnStyle}
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
