import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import PresetCard from "./PresetCard";

/**
 * A pre-styled "Advanced configuration applied" indicator card.
 * Wraps PresetCard with a "selected" state and a label showing the model name.
 *
 * @param {object}   props
 * @param {string}   props.modelName - The name of the currently configured model.
 * @param {Function} props.onClick   - Opens the advanced config modal.
 * @returns {JSX.Element} The advanced config card.
 */
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
