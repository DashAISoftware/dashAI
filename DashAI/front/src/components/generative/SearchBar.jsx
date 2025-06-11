import { TextField, InputAdornment } from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";

export default function SearchBar({ placeholder, onChange, value }) {
  return (
    <TextField
      placeholder={placeholder}
      value={value}
      onChange={onChange}
      fullWidth
      variant="outlined"
      InputProps={{
        startAdornment: (
          <InputAdornment position="start">
            <SearchIcon sx={{ color: "text.secondary" }} />
          </InputAdornment>
        ),
      }}
      sx={{
        "& .MuiOutlinedInput-root": {
          bgcolor: "background.default",
          borderRadius: 1,
        },
        "& .MuiInputBase-input": {
          color: "white",
          py: 1,
          fontSize: "0.875rem",
        },
        "& .MuiInputBase-input::placeholder": {
          color: "text.secondary",
          opacity: 1,
          fontSize: "0.875rem",
        },
      }}
    />
  );
}
