import React, { useState, useEffect } from "react";

import { Box } from "@mui/material";
import { getExplorersByNotebookId } from "../../api/notebook";
import Results from "./Results";
import ExplorerBox from "./ExplorerBox";

export default function NotebookView({ notebook }) {
  if (!notebook) {
    return null;
  }
  const [explorers, setExplorers] = useState([]);

  useEffect(() => {
    const fetchExplorers = async () => {
      const data = await getExplorersByNotebookId(notebook.id);
      setExplorers(data);
    };

    fetchExplorers();
  }, []);

  return (
    <Box>
      {explorers.map((explorer) => (
        <ExplorerBox key={explorer.id} explorer={explorer} />
      ))}
    </Box>
  );
}
