import { useState } from "react";
import { Box, Grid, Button, Alert, AlertTitle, Skeleton } from "@mui/material";
import SearchBar from "./SearchBar";
import CustomLayout from "../custom/CustomLayout";
import OptionBox from "./OptionBox";
import { useTranslation } from "react-i18next";

export default function SelectOptionMenu({
  goToPrevStep = null,
  title,
  subtitle,
  options,
  loading = false,
  searchBar = false,
  showNoDatasetAlert = false,
  onGoToDatasets = null,
  goToNextStep = null,
  dataTour = null,
  dataTourTarget = null,
}) {
  const [search, setSearch] = useState("");
  const filteredOptions = options.filter((option) =>
    option.name.toLowerCase().includes(search.toLowerCase()),
  );
  const { t } = useTranslation(["common", "datasets"]);

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
            <AlertTitle>{t("datasets:label.noDatasetsAvailable")}</AlertTitle>
            {t("datasets:label.uploadDatasetBeforeCreatingSession")}
            {onGoToDatasets && (
              <Box sx={{ mt: 1 }}>
                <Button
                  variant="contained"
                  size="small"
                  onClick={onGoToDatasets}
                >
                  {t("datasets:button.goToDatasets")}
                </Button>
              </Box>
            )}
          </Alert>
        )}

        {searchBar && (
          <Box width={"450px"}>
            <SearchBar
              placeholder={t("common:searchPlaceholder", "Search ...")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </Box>
        )}

        <Grid
          container
          direction="row"
          alignItems="stretch"
          spacing={1}
          sx={{ mt: 2, mx: 0, maxWidth: "100%" }}
        >
          {loading
            ? Array.from({ length: 6 }).map((_, index) => (
                <Grid
                  size={{ xl: 4, lg: 4, md: 6, sm: 12, xs: 12 }}
                  key={index}
                >
                  <Skeleton variant="rounded" height={100} />
                </Grid>
              ))
            : null}
          {!loading &&
            filteredOptions.map((option, index) => {
              const { name, display_name, description, Icon, ...otherProps } =
                option;

              return (
                <Grid
                  size={{ xl: 4, lg: 4, md: 6, sm: 12, xs: 12 }}
                  key={index}
                >
                  <OptionBox
                    optionName={display_name}
                    description={description}
                    onClick={() => goToNextStep(option.name)}
                    Icon={Icon}
                    dataTour={
                      dataTour && dataTourTarget && name === dataTourTarget
                        ? dataTour
                        : dataTour && !dataTourTarget
                          ? dataTour
                          : undefined
                    }
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
            {t("common:back")}
          </Button>
        )}
      </Box>
    </CustomLayout>
  );
}
