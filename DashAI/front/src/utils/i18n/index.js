import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

const localeFiles = import.meta.glob("./locales/*/*.json", {
  eager: true,
  import: "default",
});

const resources = {};
for (const [path, content] of Object.entries(localeFiles)) {
  const [, language, namespace] = path.match(
    /\.\/locales\/([^/]+)\/([^/]+)\.json$/,
  );
  resources[language] ??= {};
  resources[language][namespace] = content;
}

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    supportedLngs: ["en", "es", "pt", "de", "zh"],
    nonExplicitSupportedLngs: true,
    fallbackLng: "en",
    ns: Object.keys(resources.en),
    defaultNS: "common",

    interpolation: {
      escapeValue: false,
    },
  });

export default i18n;
