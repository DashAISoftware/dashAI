import { Box, Stack, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import SideBar from "../threeSectionLayout/panelContainers/SideBar";
import ComponentDetailsPanel from "../custom/ComponentDetailsPanel";
import FormSchemaRenderFields from "../shared/FormSchemaRenderFields";
import { useCreateSession } from "./CreateSessionContext";

export default function CreateSessionRight() {
  const { t } = useTranslation(["generative", "common"]);
  const { step, selectedModel, formik, processedProperties } = useCreateSession();

  if (step === 0) {
    return <ComponentDetailsPanel component={selectedModel} />;
  }

  return (
    <SideBar>
      <Stack spacing={2} sx={{ p: 3, height: "100%", overflowY: "auto" }}>
        <Box>
          <Typography variant="h6">{t("common:modelParameters")}</Typography>
          {selectedModel && (
            <Typography variant="caption" color="text.secondary">
              {selectedModel.display_name || selectedModel.name}
            </Typography>
          )}
        </Box>

        {Object.keys(processedProperties).length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            {t("generative:label.modelHasNoParameters")}
          </Typography>
        ) : (
          <FormSchemaRenderFields
            modelSchema={processedProperties}
            formik={formik}
            autoSave={false}
            handleUpdateSchema={(updatedValues) => {
              formik.setValues((prev) => ({ ...prev, ...updatedValues }));
            }}
            onFormSubmit={formik.handleSubmit}
            setError={(error) => console.error(error)}
            errorsMessage={formik.errors || {}}
            spacing={2}
          />
        )}
      </Stack>
    </SideBar>
  );
}
