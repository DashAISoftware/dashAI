import React from "react";
import { Paper, TextField, IconButton } from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import AddCardIcon from "@mui/icons-material/AddCard";

export default function SearchBar({ placeholder, onChange, value }) {
  return (
    <Paper
      component="form"
      sx={{
        p: "2px 4px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        width: "100%",
        borderRadius: 1,
        backgroundColor: "#161925",
      }}
    >
      <TextField
        variant="standard"
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        InputProps={{
          disableUnderline: true,
          sx: {
            color: "#ffffff",
            "& .MuiInputBase-input": {
              padding: "0px",
              marginLeft: "8px",
            },
          },
        }}
      />
      <IconButton type="button" sx={{ p: "10px" }} aria-label="search">
        <SearchIcon sx={{ color: "#ffffff" }} />
      </IconButton>
    </Paper>
  );
}
