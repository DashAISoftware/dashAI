import {
  Typography,
} from "@mui/material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import SectionCard from "../components/SectionCard";
import PromptBody from "../components/PromptBody";

export default function PromptSection({
  promptModel,
  setPromptModel,
  onTokenCountChange,
}) {
  const { t } = useTranslation(["generative"]);

  return (
    <SectionCard>
      <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
        {t("generative:simplifiedRag.prompt.description")}
      </Typography>

      <PromptBody
        promptModel={promptModel}
        setPromptModel={setPromptModel}
        onTokenCountChange={onTokenCountChange}
      />
    </SectionCard>
  );
}

PromptSection.propTypes = {
  promptModel: PropTypes.object,
  setPromptModel: PropTypes.func.isRequired,
  onTokenCountChange: PropTypes.func,
};
