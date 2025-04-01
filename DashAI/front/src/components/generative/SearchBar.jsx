import { useRef } from "react";
import { Paper, TextField, Box } from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";

export default function SearchBar({ placeholder, onChange, value }) {
  const inputRef = useRef(null);

  const handleContainerClick = () => {
    // Focus the input when clicking anywhere on the search bar
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

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
        cursor: "text", // Show text cursor on hover
        "&:hover": {
          backgroundColor: "#1e2231", // Subtle hover effect
        },
      }}
      onClick={handleContainerClick}
      onSubmit={(e) => e.preventDefault()} // Prevent form submission
    >
      <TextField
        variant="standard"
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        inputRef={inputRef}
        fullWidth
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
      <Box
        sx={{ p: "10px" }}
        aria-label="search"
        display={"flex"}
        justifyContent={"center"}
        alignItems={"center"}
      >
        <SearchIcon sx={{ color: "#ffffff" }} />
      </Box>
    </Paper>
  );
}
