import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import PresetCard from "./PresetCard";

export default function AdvancedConfigCard({ modelName, onClick }) {
  const { t } = useTranslation(["generative"]);

  return (
    <PresetCard
      selected
      label={t("generative:rag.retriever.advancedApplied")}
      description={modelName}
      onClick={onClick}
    />
  );
}

AdvancedConfigCard.propTypes = {
  modelName: PropTypes.string.isRequired,
  onClick: PropTypes.func.isRequired,
};
