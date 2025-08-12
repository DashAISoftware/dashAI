import { Box } from "@mui/material";

export default function LeftBar({ children }) {
  return (
    <Box
      width="100%"
      height="100%"
      borderRadius={2}
      display="flex"
      flexDirection="column"
      justifyContent="space-between"
      sx={{
        bgcolor: "background.box",
        color: "white",
        borderRight: "1px solid #252836",
      }}
    >
      {children}
    </Box>
  );
}
