import { Box, Typography, Paper } from "@mui/material";
import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import Upload from "../../shared/Upload"; 
let idCounter = 200;

export default function DocumentDropzone({ onAddDocument }) {
  const onDrop = useCallback((acceptedFiles) => {
    acceptedFiles.forEach((file) => {
      const newDoc = {
        id: idCounter++,
        name: file.name,
        updatedAt: new Date().toLocaleDateString(),
      };
      onAddDocument(newDoc);
    });
  }, [onAddDocument]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop });

  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2,
        height: "100%",
        backgroundColor: "background.default",
        borderStyle: isDragActive ? "dashed" : "solid",
        borderColor: isDragActive ? "primary.main" : "divider",
        borderRadius: 2,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
        transition: "border-color 0.3s",
      }}
      {...getRootProps()}
    >
      <input {...getInputProps()} />
      <Typography variant="body1" color="text.secondary">
        Drag & drop documents here, or click to upload
      </Typography>
    </Paper>
  );
}
