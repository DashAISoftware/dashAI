import { Box } from "@mui/material";
import LeftBar from "../../components/notebooks/LeftBar";
import MainBox from "../../components/notebooks/MainBox";
import RightBar from "../../components/notebooks/RightBar";

export default function Generative() {
  return (
    <Box height="calc(100vh - 74px)" width="100%" p={1.5} pb={1} display="flex">
      <Box width="22%" mr={1}>
        <LeftBar></LeftBar>
      </Box>
      <Box width="56%" mr={1}>
        <MainBox> </MainBox>
      </Box>
      <Box width="22%">
        <RightBar></RightBar>
      </Box>
    </Box>
  );
}
