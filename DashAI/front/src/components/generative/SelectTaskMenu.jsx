import { useEffect, useState, useRef } from "react";
import { Box, Typography, Autocomplete, TextField } from "@mui/material";
import TaskBox from "../../components/generative/TaskBox";
import IconAvatar from "../../components/generative/IconAvatar";
import { getGenerativeTask } from "../../api/generativeTask";
import CustomLayout from "../../components/custom/CustomLayout";

export default function SelectTaskMenu({ goToNextStep }) {
  const [task, setTask] = useState([]);

  const containerRef = useRef(null);
  const [containerWidth, setContainerWidth] = useState(0);

  useEffect(() => {
    if (!containerRef.current) return;

    const observer = new ResizeObserver((entries) => {
      for (let entry of entries) {
        setContainerWidth(entry.contentRect.width);
      }
    });

    observer.observe(containerRef.current);

    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    getGenerativeTask().then(setTask);
  }, []);

  let tasksToShow = task;

  if (containerWidth > 800) {
    tasksToShow = task.slice(0, 3);
  } else if (containerWidth > 500) {
    tasksToShow = task.slice(0, 2);
  } else {
    tasksToShow = task.slice(0, 1);
  }

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
        marginTop={5}
      >
        <Box
          ref={containerRef}
          display="flex"
          justifyContent="space-evenly"
          alignItems="stretch"
          gap={2}
          width="100%"
        >
          {tasksToShow.map((task, index) => (
            <Box
              key={index}
              flex="1 1 30%"
              maxWidth="300px"
              minWidth="200px"
              minHeight="40px"
            >
              <TaskBox
                key={index}
                taskName={task.name}
                description={task.description}
                onClick={() => goToNextStep(task.name)}
              />
            </Box>
          ))}
        </Box>

        <Autocomplete
          disablePortal
          options={task.map((t) => t.name)}
          sx={{ mt: 4, ml: 2, mr: 2 }}
          renderInput={(params) => <TextField {...params} label="Task" />}
          onChange={(event, value) => {
            const selectedTask = task.find((t) => t.name === value);
            if (selectedTask) {
              goToNextStep(selectedTask.name);
            }
          }}
        />
      </Box>
    </CustomLayout>
  );
}
