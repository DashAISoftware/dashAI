import { useState } from "react";
import PropTypes from "prop-types";
import { Box } from "@mui/material";
import { useTranslation } from "react-i18next";
import { useSnackbar } from "notistack";
import ScopeStepSessionConverter from "./ScopeStepSessionConverter";
import ParameterStepConverter from "../../notebooks/converterCreation/ParameterStepConverter";
import { updateSessionConverters } from "../../../api/modelSession";
import { pollSessionPreprocessing } from "../../../utils/sessionPreprocessing";

/**
 * Session-flow counterpart to the notebook's FormConverterSection. Same
 * Scope -> Parameters stepper shape, but saving calls the real
 * `updateSessionConverters` endpoint (a PUT that replaces the session's
 * full converter list) and then polls `pollSessionPreprocessing` until the
 * backend finishes applying it. `onApplyStart` fires synchronously right
 * as a save begins (before the PUT), so the center panel can flip its
 * isApplying state immediately rather than only learning about an in-flight
 * apply after the fact — see PreprocessingStep.jsx, which is what actually
 * disables the sidebar's converter cards while this is true, preventing a
 * second overlapping save from ever being built off a stale `session` prop.
 * The outcome is reported upward via `onApplied`/`onApplyError` so the
 * center panel can refresh its dataset table and clear that loading state.
 */
export default function FormSessionConverterSection({
  step,
  setStep,
  handleClose,
  tool,
  inputColumnNames,
  columnTypes,
  session,
  onApplyStart,
  onApplied,
  onApplyError,
}) {
  const { t } = useTranslation(["models"]);
  const { enqueueSnackbar } = useSnackbar();
  const [columns, setColumns] = useState([]);
  const [targetColumn, setTargetColumn] = useState(null);

  const hasParams = Object.values(tool.schema.properties).length > 0;

  const handleSaveConverter = async (params) => {
    // Signalled synchronously, before handleClose() and before the PUT
    // fires, so the sidebar can flip isApplying/disable its cards *before*
    // any further save can read a stale `session.converters` — closing the
    // race where a second overlapping add would silently drop the first
    // converter (the /converters endpoint does an unconditional replace).
    onApplyStart();
    const newEntry = {
      converter: tool.name,
      params: params || {},
      columns: columns.map((col) => col.columnName),
      target_column: targetColumn?.columnName ?? null,
    };
    handleClose();
    try {
      const updatedSession = await updateSessionConverters(session.id, [
        ...(session.converters || []),
        newEntry,
      ]);
      enqueueSnackbar(t("models:label.converterApplying"), {
        variant: "info",
      });
      // updatedSession reflects the converter list right after the PUT, but
      // preprocessing hasn't finished yet — pollSessionPreprocessing below
      // is what tells us when the (possibly stale) preprocessed data is
      // ready, so we don't use updatedSession directly here.
      void updatedSession;
      const cancel = pollSessionPreprocessing(session.id, {
        onFinished: (finishedSession) => {
          enqueueSnackbar(t("models:label.converterApplied"), {
            variant: "success",
          });
          onApplied(finishedSession);
        },
        onError: (erroredSession) => {
          // pollSessionPreprocessing calls this with two different shapes:
          // - terminal preprocessing_status === ERROR: onError(session)
          // - a network/request failure mid-poll: onError(null, error)
          // Never assume the first argument is a real session object.
          enqueueSnackbar(t("models:error.converterApplyFailed"), {
            variant: "error",
          });
          onApplyError(erroredSession ?? null);
        },
      });
      // onApplied/onApplyError above already stop the poller themselves
      // (pollSessionPreprocessing self-terminates on a terminal status);
      // `cancel` only matters if the owning component unmounts mid-poll —
      // Task 7 wires that cleanup at the call site that owns this modal's
      // lifetime, not here.
      void cancel;
    } catch (error) {
      enqueueSnackbar(t("models:error.converterApplyFailed"), {
        variant: "error",
      });
      onApplyError(null);
    }
  };

  return (
    <Box
      sx={{
        overflow: "visible",
        display: "flex",
        flexDirection: "column",
        flex: 1,
        maxHeight: "100%",
        minHeight: 0,
      }}
    >
      {step === 0 && (
        <ScopeStepSessionConverter
          tool={tool}
          inputColumnNames={inputColumnNames}
          columnTypes={columnTypes}
          columns={columns}
          setColumns={setColumns}
          targetColumn={targetColumn}
          setTargetColumn={setTargetColumn}
          session={session}
          nextStep={
            hasParams
              ? () => setStep((s) => s + 1)
              : () => handleSaveConverter({})
          }
        />
      )}
      {step === 1 && (
        <ParameterStepConverter
          converter={tool.name}
          tool={tool}
          selectedColumns={columns}
          initialParams={{}}
          handleSaveConverter={handleSaveConverter}
          setStep={setStep}
          saveButtonText={t("models:button.addConverter")}
        />
      )}
    </Box>
  );
}

FormSessionConverterSection.propTypes = {
  step: PropTypes.number.isRequired,
  setStep: PropTypes.func.isRequired,
  handleClose: PropTypes.func.isRequired,
  tool: PropTypes.object.isRequired,
  inputColumnNames: PropTypes.arrayOf(PropTypes.string).isRequired,
  columnTypes: PropTypes.object,
  session: PropTypes.object.isRequired,
  onApplyStart: PropTypes.func.isRequired,
  onApplied: PropTypes.func.isRequired,
  onApplyError: PropTypes.func.isRequired,
};
