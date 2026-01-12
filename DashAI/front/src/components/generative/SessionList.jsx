import { Box, Typography, Collapse } from "@mui/material";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import SessionBox from "./SessionBox";
import { useTranslation } from "react-i18next";

export default function SessionList({
  selectedSessionId,
  groupedSessions,
  openSections,
  handleSessionClick,
  handleSessionDelete,
  handleSessionInfo,
  toggleSection,
}) {
  const { t } = useTranslation(["generative"]);

  if (groupedSessions === undefined) {
    return (
      <Box
        display={"flex"}
        justifyContent={"center"}
        alignItems={"center"}
        height={"100%"}
        width={"100%"}
      >
        <Typography
          sx={{
            color: "#ffffff",
            opacity: 0.5,
            textAlign: "center",
            padding: 2,
          }}
        >
          {t("generative:label.noSessionsFound")}
        </Typography>
      </Box>
    );
  }

  return (
    <Box
      display={"flex"}
      flexDirection={"column"}
      height={"100%"}
      width={"100%"}
      pb={1}
      sx={{
        "&::-webkit-scrollbar": {
          width: "6px",
        },
        "&::-webkit-scrollbar-thumb": {
          backgroundColor: "#374151",
          borderRadius: "3px",
        },
        "&::-webkit-scrollbar-thumb:hover": {
          backgroundColor: "#4B5563",
        },
        overflowY: "auto",
        flex: 1,
      }}
    >
      {Object.keys(groupedSessions).length > 0 ? (
        Object.entries(groupedSessions).map(([taskName, taskSessions]) => (
          <Box key={taskName} mb={1}>
            {/* Task Section Header */}
            <Box
              display="flex"
              alignItems="space-between"
              sx={{
                cursor: "pointer",
                py: 0.5,
                px: 1,
                borderRadius: 1,
                "&:hover": {
                  bgcolor: "rgba(255, 255, 255, 0.05)",
                },
              }}
              onClick={() => toggleSection(taskName)}
            >
              {openSections[taskName] ? (
                <KeyboardArrowDownIcon
                  sx={{ fontSize: 20, color: "#16FFFF" }}
                />
              ) : (
                <KeyboardArrowRightIcon
                  sx={{ fontSize: 20, color: "#16FFFF" }}
                />
              )}
              <Typography
                sx={{
                  ml: 1,
                  fontSize: "0.9rem",
                  fontWeight: "medium",
                  textTransform: "capitalize",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  wordBreak: "break-all",
                  whiteSpace: "nowrap",
                  width: "100%",
                }}
              >
                {taskName}
              </Typography>
              <Box
                sx={{
                  ml: 1,
                  bgcolor: "#374151",
                  color: "white",
                  borderRadius: "50%",
                  width: 20,
                  height: 20,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 12,
                }}
              >
                {taskSessions.length}
              </Box>
            </Box>

            {/* Task Sessions */}
            <Collapse in={openSections[taskName]} timeout="auto">
              <Box pl={2}>
                {taskSessions.map((session) => (
                  <SessionBox
                    isSelected={session.id == selectedSessionId}
                    name={session.name}
                    modelName={session.model_name}
                    key={session.id}
                    id={session.id}
                    onClick={() =>
                      handleSessionClick(
                        session.id,
                        session.task_name,
                        session.display_name,
                      )
                    }
                    onDelete={handleSessionDelete}
                    onInfo={handleSessionInfo}
                  />
                ))}
              </Box>
            </Collapse>
          </Box>
        ))
      ) : (
        <Typography
          sx={{
            color: "#ffffff",
            opacity: 0.5,
            textAlign: "center",
            padding: 2,
          }}
        >
          {t("generative:label.noSessionsFound")}
        </Typography>
      )}
    </Box>
  );
}
