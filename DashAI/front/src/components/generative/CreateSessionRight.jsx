import { Box, Divider, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import SideBar from "../threeSectionLayout/panelContainers/SideBar";
import ComponentDetailsPanel from "../custom/ComponentDetailsPanel";
import FormSchemaRenderFields from "../shared/FormSchemaRenderFields";
import { useCreateSession } from "./CreateSessionContext";

export default function CreateSessionRight() {
  const { t } = useTranslation(["generative", "common"]);
  const { step, selectedModel, formik, processedProperties } = useCreateSession();

  if (step === 0) {
    return <ComponentDetailsPanel component={selectedModel} categoryKey="task_display_name" />;
  }

  return (
    <SideBar>
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          height: "100%",
          width: "100%",
        }}
      >
        {/* Title */}
        <Box
          sx={{
            p: 2,
            flexShrink: 0,
            display: "flex",
            alignItems: "center",
            height: 70,
          }}
        >
          <Typography variant="h6" color="text.primary">
            {t("common:modelParameters")}
          </Typography>
        </Box>

        <Divider sx={{ width: "100%", bgcolor: "divider" }} />

        {/* Content */}
        {Object.keys(processedProperties).length === 0 ? (
          <Box
            sx={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              p: 2,
            }}
          >
            <Typography
              variant="body2"
              color="text.secondary"
              textAlign="center"
            >
              {t("generative:label.modelHasNoParameters")}
            </Typography>
          </Box>
        ) : (
          <Box sx={{ flex: 1, overflowY: "auto", pt: 2, px: 2, pb: 5 }}>
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
          </Box>
        )}
      </Box>
    </SideBar>
  );
}
