import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import SelectOptionMenu from "../threeSectionLayout/SelectOptionMenu";
import { useGenerative } from "./GenerativeContext";
import { useTourContext } from "../tour/TourProvider";
import SimplifiedIcon from "@mui/icons-material/ViewAgenda";
import {
  ChatBubbleOutline as TextToTextIcon,
  Image as TextToImageIcon,
  Tune as ControlNetIcon,
  AutoAwesome as DefaultGenerativeIcon,
  TextSnippet as RAGIcon,
} from "@mui/icons-material";

const GENERATIVE_TASK_ICONS = {
  TextToTextGenerationTask: TextToTextIcon,
  TextToImageGenerationTask: TextToImageIcon,
  ControlNetTask: ControlNetIcon,
  RAGTask: RAGIcon,
};

export default function SelectTaskMenu() {
  const { t } = useTranslation(["generative", "common"]);
  const { tasks, setSelectedDisplayName, setSelectedTaskName, setStepIndex } =
    useGenerative();
  const tourContext = useTourContext();
  const navigate = useNavigate();

  const goToNextStep = (taskName, displayName) => {
    setSelectedDisplayName(displayName);
    setSelectedTaskName(taskName);
    setStepIndex(1);

    if (tourContext?.run && tourContext?.stepIndex === 2) {
      const waitForElement = () => {
        const element = document.querySelector('[data-tour="model-selection"]');
        if (element) {
          tourContext.nextStep();
        } else {
          setTimeout(waitForElement, 100);
        }
      };
      setTimeout(waitForElement, 100);
    }
  };

  const handleSimplifiedRAG = () => {
    navigate("/app/generative/simplified-rag");
  };

  const simplifiedRAGOption = {
    name: "simplified-rag",
    display_name: "Simplified RAG Setup",
    description: "Quick and easy RAG session setup with collapsible configuration sections",
    Icon: SimplifiedIcon,
    isCustom: true,
  };

  const allOptions = [
    ...tasks.map((task) => ({
      name: task.name,
      display_name: task.display_name,
      description: task.description,
      Icon: GENERATIVE_TASK_ICONS[task.name] || DefaultGenerativeIcon,
    })),
    simplifiedRAGOption,
  ];

  return (
    <SelectOptionMenu
      goToNextStep={(optionName) => {
        if (optionName === "simplified-rag") {
          handleSimplifiedRAG();
        } else {
          goToNextStep(
            optionName,
            tasks.find((t) => t.name === optionName)?.display_name,
          );
        }
      }}
      title={t("generative:label.generativeModule")}
      subtitle={t("generative:label.selectGenerativeTask")}
      options={allOptions}
      searchBar={true}
      dataTour="task-selection"
      dataTourTarget="TextToTextGenerationTask"
    />
  );
}
