import { useEffect, useState } from "react";
import { Box, Grid } from "@mui/material";
import TaskBox from "../../components/generative/TaskBox";
import SearchBar from "./SearchBar";
import { getGenerativeTask } from "../../api/generativeTask";
import CustomLayout from "../../components/custom/CustomLayout";
import { useTranslation } from "react-i18next";

export default function SelectTaskMenu({ goToNextStep }) {
  const [tasks, setTasks] = useState([]);
  const { t } = useTranslation(["generative", "common"]);

  useEffect(() => {
    getGenerativeTask().then(setTasks);
  }, []);

  const [search, setSearch] = useState("");

  const filteredTasks = tasks.filter((task) =>
    task.name.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <CustomLayout
      title={t("generative:label.generativeModule")}
      subtitle={t("generative:label.selectGenerativeTask")}
      padding={0}
    >
      <Box
        display={"flex"}
        height={"100%"}
        width={"100%"}
        flexDirection={"column"}
        justifyContent={"flex-start"}
      >
        <Box width={"450px"}>
          <SearchBar
            placeholder={t("generative:label.searchTasks")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </Box>

        <Grid
          container
          direction="row"
          justifyContent="flex-start"
          alignItems="stretch"
          spacing={1}
          sx={{ mt: 2, mx: 0, maxWidth: "100%" }}
        >
          {filteredTasks.map((task, index) => (
            <Grid size={{ xl: 4, lg: 6, md: 6, sm: 12, xs: 12 }} key={index}>
              <TaskBox
                taskName={task.display_name}
                description={task.description}
                onClick={() => goToNextStep(task.name, task.display_name)}
              />
            </Grid>
          ))}
        </Grid>
      </Box>
    </CustomLayout>
  );
}
