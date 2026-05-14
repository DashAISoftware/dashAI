import {
  Typography,
} from "@mui/material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import SectionCard from "../components/SectionCard";
import PromptBody from "../components/PromptBody";

export default function PromptSection({
  promptId,
  setPromptId,
  onTokenCountChange,
}) {
  const { t } = useTranslation(["generative"]);

  return (
    <SectionCard>
      <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
        {t("generative:simplifiedRag.prompt.description")}
      </Typography>

      <PromptBody
        promptId={promptId}
        setPromptId={setPromptId}
        onTokenCountChange={onTokenCountChange}
      />
    </SectionCard>
  );
}

PromptSection.propTypes = {
  promptId: PropTypes.number,
  setPromptId: PropTypes.func.isRequired,
  onTokenCountChange: PropTypes.func,
};
