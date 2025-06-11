import React, { useRef } from "react";
import { Box, InputBase } from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";

export default function SearchBar({ placeholder, onChange, value }) {
  const inputRef = useRef(null);

  const handleContainerClick = () => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  return (
    <Box
      onClick={handleContainerClick}
      sx={{
        display: "flex",
        alignItems: "center",
        bgcolor: "background.default",
        borderRadius: 1,
        px: 2,
        py: 1,
        cursor: "text",
      }}
    >
      <SearchIcon sx={{ color: "text.secondary", mr: 1 }} />
      <InputBase
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        inputRef={inputRef}
        fullWidth
        sx={{
          color: "white",
          "& .MuiInputBase-input": {
            p: 0,
          },
          "& .MuiInputBase-input::placeholder": {
            color: "text.secondary",
            opacity: 1,
          },
        }}
      />
    </Box>
  );
}
