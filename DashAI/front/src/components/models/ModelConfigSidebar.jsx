import React from "react";
import PropTypes from "prop-types";
import { Box, Typography, Button } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import SideBar from "../threeSectionLayout/panelContainers/SideBar";
import RetrainConfirmDialog from "./RetrainConfirmDialog";
import RunEditForm from "./RunEditForm";
import useRunEditForm from "../../hooks/useRunEditForm";

/**
 * Right-side panel showing and editing a run's configuration while inside
 * its full-screen model detail view — the same fields as the "Edit Run"
 * dialog, but always visible inline (like the generative session's
 * ParamsBar), instead of a separate "Configuración" tab.
 */
export default function ModelConfigSidebar({
  run,
  session,
  existingRuns = [],
  onRefresh,
}) {
  const theme = useTheme();
  const { t } = useTranslation(["models", "common"]);

  const formProps = useRunEditForm({ run, session, existingRuns, onRefresh });
  const {
    canSave,
    operationsCount,
    isSaving,
    saveConfirmOpen,
    setSaveConfirmOpen,
    doSave,
    handleSaveEdit,
  } = formProps;

  return (
    <SideBar>
      <Box
        sx={{
          p: 4,
          borderBottom: `1px solid ${theme.palette.ui.border}`,
          flexShrink: 0,
          display: "flex",
          alignItems: "center",
          height: 64,
        }}
      >
        <Typography variant="h6" color="text.primary">
          {t("models:label.configuration")}
        </Typography>
      </Box>

      <Box sx={{ flex: 1, overflowY: "auto", px: 4, pt: 4 }}>
        <RunEditForm run={run} {...formProps} />

        <Box
          sx={{
            display: "flex",
            justifyContent: "flex-end",
            pt: 2,
            pb: 4,
            position: "sticky",
            bottom: 0,
            bgcolor: "background.box",
          }}
        >
          <Button
            variant="contained"
            onClick={handleSaveEdit}
            disabled={isSaving || !canSave}
          >
            {isSaving ? t("common:saving") : t("common:save")}
          </Button>
        </Box>
      </Box>

      <RetrainConfirmDialog
        mode="save"
        open={saveConfirmOpen}
        onClose={() => setSaveConfirmOpen(false)}
        onConfirm={doSave}
        run={run}
        operationsCount={operationsCount}
      />
    </SideBar>
  );
}

ModelConfigSidebar.propTypes = {
  run: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    model_name: PropTypes.string,
    parameters: PropTypes.object,
    optimizer_name: PropTypes.string,
    optimizer_parameters: PropTypes.object,
    goal_metric: PropTypes.string,
  }).isRequired,
  session: PropTypes.shape({
    task_name: PropTypes.string,
  }),
  existingRuns: PropTypes.array,
  onRefresh: PropTypes.func,
};
