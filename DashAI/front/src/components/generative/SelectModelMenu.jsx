import React from "react";
import { Box, Typography, Autocomplete, TextField } from "@mui/material";
import IconAvatar from "../../components/generative/IconAvatar";
import { useEffect, useState } from "react";
import { getRelatedComponents } from "../../api/generativeTask";

export default function SelectModelMenu({ selectedTaskName }) {
  const [relatedComponents, setRelatedComponents] = useState([]);
  const [selectedModel, setSelectedModel] = useState(null);

  useEffect(() => {
    if (!selectedTaskName) return;

    getRelatedComponents(selectedTaskName).then(setRelatedComponents);
  }, [selectedTaskName]);

  return (
    <Box
      display={"flex"}
      height={"100%"}
      width={"100%"}
      flexDirection={"column"}
      justifyContent={"flex-start"}
    >
      <Typography
        variant="h1"
        sx={{
          fontFamily: "Roboto",
          fontSize: "16px",
          whiteSpace: "normal",
          wordBreak: "break-word",
          ml: 5,
          mt: 1,
          mr: 5,
          mb: 5,
        }}
      >
        Select a model
      </Typography>
      <Box sx={{ ml: 5 }}>
        <IconAvatar src="/dai_circle.png" size={32} />{" "}
      </Box>
      <Box
        display={"flex"}
        flexDirection={"column"}
        alignItems={"flex-start"}
        justifyContent={"center"}
        gap={1}
        sx={{ mt: 2, mb: 2, ml: 5, mr: 5 }}
      >
        <Typography
          variant="h1"
          sx={{
            fontSize: "24px",
            whiteSpace: "normal",
            wordBreak: "break-word",
            color: "#aba5a5",
          }}
        >
          Select a model from the list
        </Typography>
      </Box>
      {/* Search Bar */}
      <Autocomplete
        disablePortal
        options={relatedComponents.map((t) => t.name)}
        onChange={(event, newValue) => {
          setSelectedModel(newValue);
        }}
        sx={{ mr: 5, ml: 5, mb: 5 }}
        renderInput={(params) => <TextField {...params} label="Model" />}
      />
      {/* Model params */}
      <Box display={selectedModel ? "flex" : "none"} flexDirection={"column"}>
        {selectedModel}
      </Box>
    </Box>
  );
}
