import React from "react";
import { Grid, Typography } from "@mui/material";
import {
  FileUpload as FileUploadIcon,
  Science as ScienceIcon,
  Extension as ExtensionIcon,
  Insights as InsightsIcon,
  Merge as MergeIcon,
  Timeline as TimelineIcon,
  AutoAwesome as AutoAwesomeIcon,
} from "@mui/icons-material";
import HomeButton from "../../components/HomeButton";
import CustomLayout from "../../components/custom/CustomLayout";
import { TourProvider } from "../../components/tour/TourProvider";
import { TourButton } from "../../components/tour/TourButton";
import { TOUR_KEYS } from "../../constants/tours";

function Home() {
  return (
    <TourProvider tourKey={TOUR_KEYS.HOME}>
      <CustomLayout>
        {/* Title */}
        <Typography
          variant="h3"
          component="h1"
          color="text.primary"
          sx={{ mb: 6 }}
        >
          Welcome to DashAI!
        </Typography>
        <Typography variant="h5" component="h2" color="text.primary">
          Getting started
        </Typography>
        <Grid
          container
          direction="row"
          justifyContent="flex-start"
          alignItems="center"
          sx={{ mt: 4, mx: 0, maxWidth: "100%" }}
        >
          <Grid size={{ md: 4, sm: 6, xs: 12 }} data-tour="datasets-button">
            <HomeButton
              title="Datasets"
              description="Create and manage the datasets registered in the application."
              to="/app/data"
              Icon={FileUploadIcon}
            />
          </Grid>
          <Grid size={{ md: 4, sm: 6, xs: 12 }}>
            <HomeButton
              title="Models"
              description={
                "Configure tasks, train and compare models in " +
                "organized sessions."
              }
              to="/app/models"
              Icon={ScienceIcon}
            />
          </Grid>
          <Grid size={{ md: 4, sm: 6, xs: 12 }} data-tour="experiments-button">
            <HomeButton
              title="Experiments"
              description="Create and manage and view the status of your experiments."
              to="/app/experiments"
              Icon={ScienceIcon}
            />
          </Grid>
          <Grid
            size={{ md: 4, sm: 6, xs: 12 }}
            data-tour="explainability-button"
          >
            <HomeButton
              title="Explainers"
              description="Explore and understand the decision-making process behind your models."
              to="/app/explainers"
              Icon={InsightsIcon}
            />
          </Grid>
          {/* Pipelines button */}
          <Grid size={{ md: 4, sm: 6, xs: 12 }} data-tour="pipelines-button">
            <HomeButton
              title="Pipelines"
              description="Create and manage pipelines."
              to="/app/pipelines"
              Icon={MergeIcon}
            />
          </Grid>
        </Grid>
        <Typography
          variant="h5"
          component="h2"
          color="text.primary"
          sx={{ mt: 6 }}
        >
          Advanced
        </Typography>
        <Grid
          container
          direction="row"
          justifyContent="flex-start"
          alignItems="center"
          sx={{ mt: 4, mx: 0, maxWidth: "100%" }}
        >
          <Grid size={{ md: 4, sm: 6, xs: 12 }}>
            <HomeButton
              title="Generative"
              description={"Interact with AI models to infere."}
              to="/app/generative"
              Icon={AutoAwesomeIcon}
            />
          </Grid>
          <Grid size={{ md: 4, sm: 6, xs: 12 }}>
            <HomeButton
              title="Plugins"
              description={"Browse and manage plugins."}
              to="/app/plugins/browse"
              Icon={ExtensionIcon}
            />
          </Grid>
        </Grid>

        <TourButton tourKey={TOUR_KEYS.HOME} />
      </CustomLayout>
    </TourProvider>
  );
}

export default Home;
