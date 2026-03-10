import { Box } from "@mui/material";

export default function CenterBox({ children }) {
  return (
    <Box
      width={"100%"}
      height={"100%"}
      sx={{
        border: "0.1px solid",
        borderColor: "grey.600",
        // bgcolor: "background.paper",
      }}
      // borderRadius={2}
      overflow={"auto"}
      p={2}
    >
      {children}
    </Box>
  );
}
