import { useState } from "react";
import { Box, Grid, Button, Alert, AlertTitle } from "@mui/material";
import SearchBar from "./SearchBar";
import CustomLayout from "../custom/CustomLayout";
import OptionBox from "./OptionBox";

export default function SelectOptionMenu({
  goToNextStep,
  goToPrevStep = null,
  title,
  subtitle,
  options,
  searchBar = false,
  showNoDatasetAlert = false,
  onGoToDatasets = null,
}) {
  const [search, setSearch] = useState("");
  const filteredOptions = options.filter((option) =>
    option.name.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <CustomLayout title={title} subtitle={subtitle} padding={0}>
      <Box
        display={"flex"}
        height={"100%"}
        width={"100%"}
        flexDirection={"column"}
        justifyContent={"flex-start"}
      >
        {showNoDatasetAlert && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            <AlertTitle>No Datasets Available</AlertTitle>
            You need to upload a dataset before creating a session. Please go to
            the Dataset Module to upload your data.
            {onGoToDatasets && (
              <Box sx={{ mt: 1 }}>
                <Button
                  variant="contained"
                  size="small"
                  onClick={onGoToDatasets}
                >
                  Go to Datasets
                </Button>
              </Box>
            )}
          </Alert>
        )}

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
            const { name, display_name, description, Icon, ...otherProps } =
              option;

            return (
              <Grid size={{ xl: 6, lg: 6, md: 6, sm: 12, xs: 12 }} key={index}>
                <OptionBox
                  optionName={display_name}
                  description={description}
                  onClick={() => goToNextStep(option.name)}
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
          mt: 4,
        }}
      >
        {goToPrevStep && (
          <Button variant="outlined" onClick={goToPrevStep}>
            Back
          </Button>
        )}
      </Box>
    </CustomLayout>
  );
}
