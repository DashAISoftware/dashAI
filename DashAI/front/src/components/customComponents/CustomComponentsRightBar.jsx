import React from "react";
import {
  Box,
  Divider,
  Stack,
  TextField,
  Typography,
  CircularProgress,
  Tabs,
  Tab,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import SideBar from "../threeSectionLayout/panelContainers/SideBar";
import BaseClassSelector from "./BaseClassSelector";
import MethodSkeletonPanel from "./MethodSkeletonPanel";
import { useCustomComponents } from "./CustomComponentsContext";

export default function CustomComponentsRightBar() {
  const { t } = useTranslation(["customComponents", "common"]);
  const {
    baseClasses,
    baseInfo,
    loadingBaseInfo,
    draft,
    setDraftField,
    classNameValid,
  } = useCustomComponents();
  const [tab, setTab] = React.useState(0);

  return (
    <SideBar>
      <Box display="flex" flexDirection="column" height="100%">
        <Box p={1.5} borderBottom="1px solid" borderColor="divider">
          <Typography variant="subtitle2" gutterBottom>
            {t("rightBar.title")}
          </Typography>
          <Stack spacing={1.5}>
            <BaseClassSelector
              value={draft.base_class}
              onChange={(v) => setDraftField({ base_class: v })}
              options={baseClasses}
              disabled={!draft.isNew}
            />
            <TextField
              fullWidth
              size="small"
              label={t("fields.className")}
              value={draft.class_name}
              onChange={(e) => setDraftField({ class_name: e.target.value })}
              error={draft.class_name.length > 0 && !classNameValid}
              helperText={
                draft.class_name.length > 0 && !classNameValid
                  ? t("fields.classNameHelp")
                  : t("fields.classNameHint")
              }
            />
            <TextField
              fullWidth
              size="small"
              label={t("fields.description")}
              value={draft.description}
              onChange={(e) => setDraftField({ description: e.target.value })}
              multiline
              maxRows={3}
            />
          </Stack>
        </Box>

        <Tabs
          value={tab}
          onChange={(_, v) => setTab(v)}
          variant="fullWidth"
          sx={{
            minHeight: 36,
            borderBottom: "1px solid",
            borderColor: "divider",
          }}
        >
          <Tab
            sx={{ minHeight: 36, fontSize: 12 }}
            label={t("rightBar.tabMethods")}
          />
          <Tab
            sx={{ minHeight: 36, fontSize: 12 }}
            label={t("rightBar.tabDocs")}
          />
        </Tabs>

        <Box flexGrow={1} overflow="auto">
          {loadingBaseInfo ? (
            <Box display="flex" justifyContent="center" py={4}>
              <CircularProgress size={20} />
            </Box>
          ) : tab === 0 ? (
            <MethodSkeletonPanel baseInfo={baseInfo} />
          ) : (
            <Box p={2}>
              {baseInfo?.docstring ? (
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ whiteSpace: "pre-wrap", fontFamily: "inherit" }}
                >
                  {baseInfo.docstring}
                </Typography>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  {t("rightBar.noDocs")}
                </Typography>
              )}
              {baseInfo?.import_path && (
                <>
                  <Divider sx={{ my: 1.5 }} />
                  <Typography variant="caption" color="text.secondary">
                    {t("rightBar.importPath")}
                  </Typography>
                  <Typography
                    variant="body2"
                    sx={{ fontFamily: "monospace", fontSize: 12 }}
                  >
                    {baseInfo.import_path}
                  </Typography>
                </>
              )}
            </Box>
          )}
        </Box>
      </Box>
    </SideBar>
  );
}
