import { Box } from "@mui/material";

export default function RightBar({ children }) {
  return (
    <Box
      display={"flex"}
      height={"100%"}
      width={"100%"}
      flexDirection={"column"}
      justifyContent={"flex-start"}
      overflow={"auto"}
      bgcolor={"background.box"}
      borderRadius={2}
    >
      {children}
    </Box>
  );
}
