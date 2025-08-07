import { Box } from "@mui/material";

export default function MainBox({ children }) {
  return (
    <Box
      width={"100%"}
      height={"100%"}
      sx={{
        border: "0.2px solid",
        borderColor: "grey.600",
      }}
      borderRadius={2}
      overflow={"auto"}
      p={2}
    >
      {children}
    </Box>
  );
}
