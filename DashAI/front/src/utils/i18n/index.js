import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import configurableObjectEN from "./locales/en/configurableObject.json";
import configurableObjectES from "./locales/es/configurableObject.json";
import commonEN from "./locales/en/common.json";
import commonES from "./locales/es/common.json";
import customEN from "./locales/en/custom.json";
import customES from "./locales/es/custom.json";

// the translations
// (tip move them in a JSON file and import them,
// or even better, manage them separated from your code: https://react.i18next.com/guides/multiple-translation-files)
const resources = {
  en: {
    configurableObject: configurableObjectEN,
    common: commonEN,
    custom: customEN,
  },
  es: {
    configurableObject: configurableObjectES,
    common: commonES,
    custom: customES,
  },
};

i18n.use(initReactI18next).init({
  resources,

  lng: "en",
  fallbackLng: "en",

  ns: ["common", "custom", "configurableObject"],
  defaultNS: "common",

  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
