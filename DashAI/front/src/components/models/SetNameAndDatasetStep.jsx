import PropTypes from "prop-types";
import { Box, TextField } from "@mui/material";
import { useTranslation } from "react-i18next";

function SetNameAndDatasetStep({ formik, nameError }) {
  const { t } = useTranslation(["models"]);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <TextField
        id="session-name"
        label={t("models:label.sessionName")}
        name="name"
        variant="outlined"
        fullWidth
        value={formik.values.name}
        onChange={formik.handleChange}
        onBlur={formik.handleBlur}
        error={Boolean(nameError)}
        helperText={nameError}
      />
    </Box>
  );
}

SetNameAndDatasetStep.propTypes = {
  formik: PropTypes.object.isRequired,
  nameError: PropTypes.string,
};

export default SetNameAndDatasetStep;
