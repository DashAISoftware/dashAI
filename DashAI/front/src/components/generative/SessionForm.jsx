import { Box, TextField, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import FormSchemaRenderFields from "../shared/FormSchemaRenderFields";

export default function SessionForm({
  formik,
  processedProperties,
  nameError,
  nameErrorMessage,
  onNameChange,
}) {
  const { t } = useTranslation(["generative", "common"]);

  return (
    <form onSubmit={formik.handleSubmit}>
      <Box width="100%" mb={2} data-tour="model-parameters">
        <Typography
          sx={{
            fontSize: "16px",
            whiteSpace: "normal",
            wordBreak: "break-word",
            mb: 2,
          }}
        >
          {t("common:parameters")}
        </Typography>
        <FormSchemaRenderFields
          modelSchema={processedProperties}
          formik={formik}
          autoSave={false}
          handleUpdateSchema={(updatedValues) => {
            formik.setValues((prevValues) => ({
              ...prevValues,
              ...updatedValues,
            }));
          }}
          onFormSubmit={formik.handleSubmit}
          setError={(error) => console.error(error)}
          errorsMessage={formik.errors}
          spacing={2}
        />
      </Box>

      <Typography
        sx={{
          fontSize: "16px",
          whiteSpace: "normal",
          wordBreak: "break-word",
          mb: 2,
        }}
      >
        {t("generative:label.nameYourSession")}
      </Typography>

      <TextField
        fullWidth
        label={t("generative:label.sessionName")}
        name="name"
        value={formik.values.name}
        onChange={onNameChange}
        error={nameError}
        helperText={nameErrorMessage}
        sx={{ mb: 2 }}
      />

      <TextField
        fullWidth
        label={t("generative:label.sessionDescription")}
        name="description"
        value={formik.values.description}
        onChange={formik.handleChange}
        error={Boolean(formik.errors.description)}
        helperText={formik.errors.description}
        sx={{ mb: 2 }}
      />
    </form>
  );
}
