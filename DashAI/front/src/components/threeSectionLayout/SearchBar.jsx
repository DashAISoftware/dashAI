import { TextField, InputAdornment } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import SearchIcon from "@mui/icons-material/Search";

export default function SearchBar({ placeholder, onChange, value }) {
  const theme = useTheme();

  return (
    <TextField
      placeholder={placeholder}
      value={value}
      onChange={onChange}
      fullWidth
      variant="outlined"
      sx={{
        "& .MuiOutlinedInput-root": {
          bgcolor: theme.palette.background.default,
          borderRadius: 1,
        },
        "& .MuiInputBase-input": {
          color: theme.palette.text.primary,
          py: 2,
          fontSize: "0.875rem",
        },
        "& .MuiInputBase-input::placeholder": {
          color: theme.palette.text.secondary,
          opacity: 1,
          fontSize: "0.875rem",
        },
      }}
      slotProps={{
        input: {
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon color="action" />
            </InputAdornment>
          ),
        },
      }}
    />
  );
}
