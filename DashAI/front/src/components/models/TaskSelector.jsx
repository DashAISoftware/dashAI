import {
  Box,
  Typography,
  Card,
  CardContent,
  CardActionArea,
} from "@mui/material";
import { CheckCircle } from "@mui/icons-material";
import { useTranslation } from "react-i18next";

export default function TaskSelector({ tasks, selectedTask, onTaskSelect }) {
  const { t } = useTranslation(["models"]);

  return (
    <Box>
      <Typography variant="h6" sx={{ mb: 4 }}>
        {t("models:label.selectTask")}
      </Typography>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
          gap: 4,
        }}
      >
        {tasks.map((task) => {
          const isSelected = selectedTask?.name === task.name;
          const displayName =
            task.metadata?.display_name ||
            task.name
              .replace("Task", "")
              .replace(/([A-Z])/g, " $1")
              .trim();

          return (
            <Card
              key={task.name}
              sx={{
                border: isSelected ? 2 : 1,
                borderColor: isSelected ? "primary.main" : "divider",
                position: "relative",
              }}
            >
              <CardActionArea onClick={() => onTaskSelect(task)}>
                <CardContent>
                  {isSelected && (
                    <CheckCircle
                      sx={{
                        position: "absolute",
                        top: 8,
                        right: 8,
                        color: "primary.main",
                      }}
                    />
                  )}
                  <Typography variant="h6" gutterBottom>
                    {displayName}
                  </Typography>
                  {task.metadata?.description && (
                    <Typography variant="body2" color="text.secondary">
                      {task.metadata.description}
                    </Typography>
                  )}
                </CardContent>
              </CardActionArea>
            </Card>
          );
        })}
      </Box>
    </Box>
  );
}
