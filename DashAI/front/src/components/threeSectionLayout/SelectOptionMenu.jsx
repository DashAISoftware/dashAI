import { useState } from "react";
import { Box, Grid, Button } from "@mui/material";
import SearchBar from "./SearchBar";
import CustomLayout from "../custom/CustomLayout";
import OptionBox from "./OptionBox";
import { useTourContext } from "../tour/TourProvider";

export default function SelectOptionMenu({
  goToNextStep,
  goToPrevStep = null,
  title,
  subtitle,
  options,
  searchBar = false,
}) {
  const [search, setSearch] = useState("");
  const tourContext = useTourContext();

  const filteredOptions = options.filter((option) =>
    option.name.toLowerCase().includes(search.toLowerCase()),
  );

const handleOptionClick = (optionName) => {
  const selectedOption = options.find(option => option.name === optionName);
  if (selectedOption?.disabled) {
    return;
  }
  
  if (optionName === "sample" && tourContext?.run) {
    try {
      tourContext.nextStep();
      setTimeout(() => {
        goToNextStep(optionName);
      }, 100);
    } catch (error) {
      console.error('[SelectOptionMenu] Error advancing tour:', error);
      goToNextStep(optionName);
    }
  } else {
    goToNextStep(optionName);
  }
}; 

  return (
    <CustomLayout title={title} subtitle={subtitle} padding={0}>
      <Box
        display={"flex"}
        height={"100%"}
        width={"100%"}
        flexDirection={"column"}
        justifyContent={"flex-start"}
      >
        {searchBar && (
          <Box width={"450px"}>
            <SearchBar
              placeholder="Search ..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </Box>
        )}

        <Grid
          container
          direction="row"
          justifyContent="center"
          alignItems="stretch"
          spacing={1}
          sx={{ mt: 2, mx: 0, maxWidth: "100%" }}
        >
          {filteredOptions.map((option, index) => {
            const { name, display_name, description, Icon, ...otherProps } = option;
            
            return (
              <Grid item xl={4} lg={6} md={6} sm={12} xs={12} key={index}>
                <OptionBox
                  optionName={display_name}
                  description={description}
                  onClick={() => handleOptionClick(name)}
                  Icon={Icon}
                  {...otherProps}
                />
              </Grid>
            );
          })}
        </Grid>
      </Box>

      <Box
        sx={{
          display: "flex",
          justifyContent: "flex-end",
          mt: 2,
        }}
      >
        {goToPrevStep && (
          <Button variant="outlined" onClick={goToPrevStep} sx={{ mr: 1 }}>
            Back
          </Button>
        )}
      </Box>
    </CustomLayout>
  );
}