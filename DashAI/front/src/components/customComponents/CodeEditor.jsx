import React from "react";
import Editor from "@monaco-editor/react";
import { Box, Paper } from "@mui/material";

function CodeEditor({ value, onChange, height = "100%", readOnly = false }) {
  return (
    <Paper
      variant="outlined"
      sx={{ height, overflow: "hidden", borderRadius: 1 }}
    >
      <Box sx={{ height: "100%" }}>
        <Editor
          height="100%"
          language="python"
          theme="vs-dark"
          value={value}
          onChange={(val) => onChange(val ?? "")}
          options={{
            readOnly,
            minimap: { enabled: false },
            fontSize: 13,
            automaticLayout: true,
            scrollBeyondLastLine: false,
            tabSize: 4,
            insertSpaces: true,
            wordWrap: "on",
            bracketPairColorization: { enabled: true },
            suggestOnTriggerCharacters: true,
          }}
        />
      </Box>
    </Paper>
  );
}

export default CodeEditor;
