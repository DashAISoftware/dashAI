import React, { useState } from "react";
import { Edit } from "@mui/icons-material";
import { IconButton, Tooltip } from "@mui/material";

import RunInfoModal from "./RunInfoModal";
import { useTranslation } from "react-i18next";

export default function EditRunDialog({ experiment, run, setRun }) {
  const isRunning = run.status === 1 || run.status === 2;
  if (isRunning) {
    return null;
  }
  const [open, setOpen] = useState(false);
  const { t } = useTranslation("experiments");

  return (
    <>
      <Tooltip title={t("button.editRun")}>
        <span>
          <IconButton
            size="small"
            aria-label={t("button.editRun")}
            onClick={() => setOpen(true)}
          >
            <Edit />
          </IconButton>
        </span>
      </Tooltip>
      {open && (
        <RunInfoModal
          experiment={experiment}
          run={run}
          open={open}
          onClose={() => setOpen(false)}
          setRun={setRun}
        />
      )}
    </>
  );
}
