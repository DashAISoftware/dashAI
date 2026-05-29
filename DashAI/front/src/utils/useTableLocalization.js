import { useTranslation } from "react-i18next";
import { MRT_Localization_EN } from "material-react-table/locales/en";
import { MRT_Localization_ES } from "material-react-table/locales/es";
import { MRT_Localization_PT_BR } from "material-react-table/locales/pt-BR";

const LOCALIZATIONS = {
  en: MRT_Localization_EN,
  es: MRT_Localization_ES,
  pt: MRT_Localization_PT_BR,
};

export function useTableLocalization() {
  const { i18n } = useTranslation();
  const lang = (i18n.language || "en").split("-")[0].toLowerCase();
  return LOCALIZATIONS[lang] || MRT_Localization_EN;
}
