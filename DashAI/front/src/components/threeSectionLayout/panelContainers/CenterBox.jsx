import { Box } from "@mui/material";

export default function CenterBox({ children }) {
  return (
    <Box
      width={"100%"}
      height={"100%"}
      sx={{
        display: "flex",
        flexDirection: "column",
        overflow: "auto",
        p: 2,
      }}
    >
      {children}
    </Box>
  );
}
