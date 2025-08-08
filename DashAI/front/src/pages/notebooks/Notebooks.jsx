import { useState } from "react";
import { Box } from "@mui/material";
import LeftBar from "../../components/notebooks/LeftBar";
import MainBox from "../../components/notebooks/MainBox";
import RightBar from "../../components/notebooks/RightBar";
import SelectOptionMenu from "../../components/threeSectionLayout/SelectOptionMenu";
import UploadDatasetSteps from "../../components/notebooks/UploadDatasetSteps";

export default function Generative() {
  const [step, setStep] = useState(0);
  const [selectedOption, setSelectedOption] = useState(null);

  const goToNextStep = (option = selectedOption) => {
    setStep((prevStep) => prevStep + 1);
    setSelectedOption(option);
  };

  return (
    <Box height="calc(100vh - 74px)" width="100%" p={1.5} pb={1} display="flex">
      <Box width="22%" mr={1}>
        <LeftBar></LeftBar>
      </Box>
      <Box width="56%" mr={1}>
        <MainBox>
          {step === 0 && (
            <SelectOptionMenu
              title="Dataset Module"
              subtitle="Upload your datasets: Explore, analyze, and transform your data with advanced exploratory analysis tools. Create interactive notebooks, generate visualizations, and apply data transformations intuitively."
              options={[
                {
                  name: "dataset",
                  display_name: "Upload Dataset",
                  description:
                    "Import your data from various sources and formats.",
                  Icon: null,
                },
                {
                  name: "notebook",
                  display_name: "Create a New Notebook",
                  description:
                    "Start a new analysis session with an existing dataset.",
                  Icon: null,
                },
              ]}
              searchBar={false}
              goToNextStep={goToNextStep}
            />
          )}
          {step === 1 && selectedOption === "dataset" && (
            <UploadDatasetSteps
              backHome={() => {
                setStep(0);
                setSelectedOption(null);
              }}
            />
          )}
        </MainBox>
      </Box>
      <Box width="22%">
        <RightBar></RightBar>
      </Box>
    </Box>
  );
}
