import { useCallback, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { Box, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import { getDatasetTypes as getDatasetTypesRequest } from "../../api/datasets";
import { useModels } from "./ModelsContext";
import { useExplorersAndConverters } from "../notebooks/context/ExplorersAndConvertersContext";
import SelectConvertersStep from "./modelSession/SelectConvertersStep";
import SessionConvertersRightBar from "./modelSession/SessionConvertersRightBar";
import StepperNavigationFooter from "../shared/StepperNavigationFooter";

/**
 * Second (final) wizard step: optional converters, configured via the
 * sidebar pushed into `sessionRightContent`. Session creation happens from
 * this step's "Crear sesión" button, not step one's.
 */
function PreprocessingStep({
  newExp,
  setNewExp,
  dataset,
  onBack,
  onCreateSession,
}) {
  const { setSessionRightContent } = useModels();
  const { t } = useTranslation(["models", "datasets", "common"]);
  const theme = useTheme();
  const { setPendingDropTool } = useExplorersAndConverters();
  const [columnTypes, setColumnTypes] = useState({});
  const [isDragOver, setIsDragOver] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  // Mirrors the notebook's NotebookView.jsx drop target: same window-level
  // dragstart/dragend listeners driving the same "is a converter card being
  // dragged right now" overlay, so dropping one here behaves exactly like
  // dropping it onto the sidebar's own cards.
  useEffect(() => {
    const onStart = (e) => {
      if (e.dataTransfer.types.includes("application/x-dashai-tool")) {
        setIsDragging(true);
      }
    };
    const onEnd = () => {
      setIsDragging(false);
      setIsDragOver(false);
    };
    window.addEventListener("dragstart", onStart);
    window.addEventListener("dragend", onEnd);
    return () => {
      window.removeEventListener("dragstart", onStart);
      window.removeEventListener("dragend", onEnd);
    };
  }, []);

  const handleDragOver = (e) => {
    if (!e.dataTransfer.types.includes("application/x-dashai-tool")) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  };

  const handleDragEnter = (e) => {
    if (!e.dataTransfer.types.includes("application/x-dashai-tool")) return;
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    const related = e.relatedTarget;
    if (!related || !e.currentTarget.contains(related)) {
      setIsDragOver(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    try {
      const tool = JSON.parse(
        e.dataTransfer.getData("application/x-dashai-tool"),
      );
      if (tool?.name) setPendingDropTool(tool);
    } catch {
      // ignore invalid drops
    }
  };

  useEffect(() => {
    let isMounted = true;
    getDatasetTypesRequest(dataset.id)
      .then((types) => {
        if (isMounted) setColumnTypes(types || {});
      })
      .catch((error) => console.error("Error fetching dataset types:", error));
    return () => {
      isMounted = false;
    };
  }, [dataset.id]);

  // useCallback keeps this reference stable across renders (setNewExp itself
  // never changes), so it's safe to list in the effect below without that
  // effect re-running — and re-pushing a brand-new sidebar element — every
  // time newExp changes for unrelated reasons (e.g. a converter being added).
  const handleAddConverter = useCallback(
    (converter) =>
      setNewExp((prev) => ({
        ...prev,
        converters: [...(prev.converters || []), converter],
      })),
    [setNewExp],
  );

  useEffect(() => {
    setSessionRightContent(
      <SessionConvertersRightBar
        dataset={dataset}
        inputColumnNames={newExp.input_columns}
        columnTypes={columnTypes}
        onAddConverter={handleAddConverter}
      />,
    );
    return () => setSessionRightContent(null);
  }, [dataset, newExp.input_columns, columnTypes, handleAddConverter]);

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        minHeight: 0,
      }}
    >
      <Box sx={{ mb: 4 }}>
        <Typography variant="h5" component="h1">
          {t("models:label.sessionConverters")}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {t("models:label.sessionConvertersDescription")}
        </Typography>
      </Box>
      <Box
        onDragOver={handleDragOver}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        sx={{
          flex: 1,
          minHeight: 0,
          overflowY: "auto",
          pt: 2,
          position: "relative",
          outline: isDragOver
            ? `2px dashed ${theme.palette.primary.main}`
            : isDragging
              ? `2px dashed ${theme.palette.divider}`
              : "none",
          transition: "outline 0.15s",
        }}
      >
        {isDragging && (
          <Box
            sx={{
              position: "absolute",
              inset: 0,
              zIndex: 10,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              bgcolor: isDragOver
                ? `${theme.palette.primary.main}14`
                : theme.palette.action.hover,
              pointerEvents: "none",
              transition: "background-color 0.15s",
            }}
          >
            <Typography
              variant="h6"
              sx={{
                color: isDragOver
                  ? theme.palette.primary.main
                  : theme.palette.text.secondary,
                fontWeight: 600,
                pointerEvents: "none",
                transition: "color 0.15s",
              }}
            >
              {t("datasets:label.dropToolHere")}
            </Typography>
          </Box>
        )}
        <SelectConvertersStep newExp={newExp} setNewExp={setNewExp} />
      </Box>
      <StepperNavigationFooter
        onBack={onBack}
        onNext={onCreateSession}
        nextLabel={t("models:button.createSession")}
      />
    </Box>
  );
}

PreprocessingStep.propTypes = {
  newExp: PropTypes.shape({
    input_columns: PropTypes.arrayOf(PropTypes.string),
    converters: PropTypes.array,
  }).isRequired,
  setNewExp: PropTypes.func.isRequired,
  dataset: PropTypes.object.isRequired,
  onBack: PropTypes.func.isRequired,
  onCreateSession: PropTypes.func.isRequired,
};

export default PreprocessingStep;
