import { useState, useCallback } from "react";
import { useSnackbar } from "notistack";
import {
  getModelSessions,
  updateModelSession,
  deleteModelSession,
} from "../../api/modelSession";
import { getComponents } from "../../api/component";

export function useSessions({ t }) {
  const { enqueueSnackbar } = useSnackbar();
  const [tasks, setTasks] = useState([]);
  const [selectedTask, setSelectedTask] = useState(null);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [selectedSession, setSelectedSession] = useState(null);
  const [sessions, setSessions] = useState([]);

  // -------- actions --------

  const fetchSessions = useCallback(async () => {
    try {
      const data = await getModelSessions();
      setSessions(data);
    } catch (error) {
      enqueueSnackbar(t("models:error.failedToFetchSessions"), {
        variant: "error",
      });
      console.error("Failed to fetch sessions:", error);
    }
  }, [enqueueSnackbar, t]);

  const fetchTasks = useCallback(async () => {
    try {
      const data = await getComponents({
        selectTypes: ["Task"],
        hasRelatedOfType: "Model",
      });
      setTasks(data);
    } catch (error) {
      enqueueSnackbar(t("models:error.failedToFetchTasks"), {
        variant: "error",
      });
      console.error("Failed to fetch tasks:", error);
    }
  }, [enqueueSnackbar, t]);

  const editSession = async (sessionId, newName) => {
    try {
      const result = await updateModelSession({
        id: sessionId,
        formData: { name: newName },
      });
      setSessions((prev) =>
        prev.map((session) =>
          session.id === sessionId
            ? { ...session, name: result.name }
            : session,
        ),
      );
      enqueueSnackbar(t("models:message.sessionUpdated"), {
        variant: "success",
      });
    } catch (error) {
      console.error("Failed to update session:", error);
      if (error.response?.status === 409) {
        enqueueSnackbar(t("models:error.sessionNameExists"), {
          variant: "error",
        });
      } else if (error.response?.status === 422) {
        enqueueSnackbar(t("models:error.sessionNameEmpty"), {
          variant: "error",
        });
      } else {
        enqueueSnackbar(t("models:error.failedToUpdateSession"), {
          variant: "error",
        });
      }
      throw error;
    }
  };

  const deleteSessionById = async (id) => {
    try {
      await deleteModelSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      return true;
    } catch (error) {
      enqueueSnackbar(t("models:error.failedToDeleteSession"), {
        variant: "error",
      });
      console.error("Error deleting session:", error);
    }
    return false;
  };

  return {
    tasks,
    setTasks,
    selectedTask,
    setSelectedTask,
    selectedSessionId,
    setSelectedSessionId,
    selectedSession,
    setSelectedSession,
    sessions,
    setSessions,
    fetchSessions,
    fetchTasks,
    editSession,
    deleteSessionById,
  };
}
