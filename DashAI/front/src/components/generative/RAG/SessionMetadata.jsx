import React, { useEffect } from "react";
import PropTypes from "prop-types";
import { Box, TextField, Typography } from "@mui/material";
import { useFormik } from "formik";
import * as yup from "yup";

const validationSchema = yup.object({
  name: yup.string().required("Session name is required"),
  description: yup.string()
});

function SessionMetadata({ 
  sessionData, 
  onUpdate, 
  setNextEnabled 
}) {
  const formik = useFormik({
    initialValues: {
      name: sessionData.name || "",
      description: sessionData.description || ""
    },
    validationSchema,
    onSubmit: (values) => {
      onUpdate(values);
    }
  });

  useEffect(() => {
    // Enable next button if form is valid
    setNextEnabled(formik.isValid);
    
    // Auto-update parent component when values change
    if (formik.isValid) {
      onUpdate({
        name: formik.values.name,
        description: formik.values.description
      });
    }
  }, [formik.values, formik.isValid]);

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Session Information
      </Typography>
      
      <TextField
        fullWidth
        id="name"
        name="name"
        label="Session Name"
        value={formik.values.name}
        onChange={formik.handleChange}
        error={formik.touched.name && Boolean(formik.errors.name)}
        helperText={formik.touched.name && formik.errors.name}
        margin="normal"
      />
      
      <TextField
        fullWidth
        id="description"
        name="description"
        label="Session Description"
        multiline
        rows={4}
        value={formik.values.description}
        onChange={formik.handleChange}
        error={formik.touched.description && Boolean(formik.errors.description)}
        helperText={formik.touched.description && formik.errors.description}
        margin="normal"
      />
    </Box>
  );
}

SessionMetadata.propTypes = {
  sessionData: PropTypes.object.isRequired,
  onUpdate: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired
};

export default SessionMetadata;