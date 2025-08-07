import { Box } from "@mui/material";
import Footer from "./Footer";
import BackToModuleHomeButton from "./BackToModuleHomeButton";

export default function LeftBar({ children }) {
  return (
    <Box
      width="100%"
      height="100%"
      borderRadius={2}
      display={"flex"}
      flexDirection={"column"}
      justifyContent={"space-between"}
      sx={{
        bgcolor: "background.box",
        color: "white",
        display: "flex",
        flexDirection: "column",
        borderRight: "1px solid #252836",
      }}
    >
      {children}
      <Footer />
    </Box>
  );
}
