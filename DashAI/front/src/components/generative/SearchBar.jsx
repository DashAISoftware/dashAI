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
        bgcolor: "#1A1E2E",
        borderRadius: 1,
        px: 2,
        py: 1,
        cursor: "text",
        "&:hover": {
          bgcolor: "#1E2231",
        },
      }}
    >
      <SearchIcon sx={{ color: "#6E7191", mr: 1 }} />
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
            color: "#6E7191",
            opacity: 1,
          },
        }}
      />
    </Box>
  );
}
