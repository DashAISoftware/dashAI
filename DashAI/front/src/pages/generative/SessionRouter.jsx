import { useState, useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import { Box, CircularProgress, Typography } from "@mui/material";
import { getGenerativeSession } from "../../api/generativeTask";
import Generative from "./Generative";
import { GenerativeProvider } from "../../components/generative/GenerativeContext";
import RAGSessionPage from "./rag-session/RAGSessionPage";

export default function SessionRouter() {
  const { id } = useParams();
  const [taskName, setTaskName] = useState(null);
  const [loading, setLoading] = useState(false);
  const prevViewRef = useRef({ taskName: null, loaded: false });

  useEffect(() => {
    const sid = Number(id);
    if (!Number.isFinite(sid) || sid <= 0) {
      setTaskName(null);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);

    getGenerativeSession(sid)
      .then((session) => {
        if (!cancelled) {
          const tn = session?.task_name || null;
          setTaskName(tn);
          prevViewRef.current = { taskName: tn, loaded: true };
        }
      })
      .catch(() => {
        if (!cancelled) {
          setTaskName(null);
          prevViewRef.current = { taskName: null, loaded: true };
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [id]);

  const effectiveView = loading ? prevViewRef.current.taskName : taskName;
  const isFirstLoad = !prevViewRef.current.loaded && loading;

  if (isFirstLoad) {
    return (
      <Box display="flex" alignItems="center" justifyContent="center" height="100vh">
        <CircularProgress />
      </Box>
    );
  }

  if (!effectiveView) {
    return (
      <Box display="flex" alignItems="center" justifyContent="center" height="100vh">
        <Typography variant="h6" color="text.secondary">
          Session not found
        </Typography>
      </Box>
    );
  }

  if (effectiveView === "RAGTask") {
    return (
      <GenerativeProvider key={id}>
        <RAGSessionPage />
      </GenerativeProvider>
    );
  }

  return <Generative key={id} />;
}
