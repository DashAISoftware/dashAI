import { useEffect, useState, useRef } from "react";
import { Box, Typography, Autocomplete, TextField, Grid } from "@mui/material";
import TaskBox from "../../components/generative/TaskBox";
import IconAvatar from "../../components/generative/IconAvatar";
import { getGenerativeTask } from "../../api/generativeTask";
import CustomLayout from "../../components/custom/CustomLayout";

export default function SelectTaskMenu({ goToNextStep }) {
  const [tasks, setTasks] = useState([]);

  useEffect(() => {
    getGenerativeTask().then(setTasks);
  }, []);

  return (
    <CustomLayout
      title="Generative Module"
      subtitle="Select generative task to start a new session"
      padding={0}
    >
      <Box
        display={"flex"}
        height={"100%"}
        width={"100%"}
        flexDirection={"column"}
        justifyContent={"flex-start"}
        //marginTop={5}
      >
        <Grid
          container
          direction="row"
          justifyContent="flex-start"
          alignItems="center"
          spacing={1}
          sx={{ mt: 2, mx: 0, maxWidth: "100%" }}
        >
          {tasks.map((task, index) => (
            <Grid item xl={4} lg={6} md={6} sm={12} xs={12}>
              <TaskBox
                key={index}
                taskName={task.name}
                description={task.description}
                onClick={() => goToNextStep(task.name)}
              />
            </Grid>
          ))}
        </Grid>

        <Autocomplete
          disablePortal
          options={tasks.map((t) => t.name)}
          sx={{ mt: 4, ml: 2, mr: 2 }}
          renderInput={(params) => <TextField {...params} label="Task" />}
          onChange={(event, value) => {
            const selectedTask = tasks.find((t) => t.name === value);
            if (selectedTask) {
              goToNextStep(selectedTask.name);
            }
          }}
        />
      </Box>
    </CustomLayout>
  );
}
