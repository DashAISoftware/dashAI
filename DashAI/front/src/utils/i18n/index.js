import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import configurableObjectEN from "./locales/en/configurableObject.json";
import configurableObjectES from "./locales/es/configurableObject.json";
import commonEN from "./locales/en/common.json";
import commonES from "./locales/es/common.json";
import customEN from "./locales/en/custom.json";
import customES from "./locales/es/custom.json";
import experimentsEN from "./locales/en/experiments.json";
import experimentsES from "./locales/es/experiments.json";
import explainersEN from "./locales/en/explainers.json";
import explainersES from "./locales/es/explainers.json";
import generativeEN from "./locales/en/generative.json";
import generativeES from "./locales/es/generative.json";
import modelsEN from "./locales/en/models.json";
import modelsES from "./locales/es/models.json";
import datasetsEN from "./locales/en/datasets.json";
import datasetsES from "./locales/es/datasets.json";
import predictionEN from "./locales/en/prediction.json";
import predictionES from "./locales/es/prediction.json";
import homeTourEN from "./locales/en/homeTour.json";
import homeTourES from "./locales/es/homeTour.json";
import notebookTourEN from "./locales/en/notebookTour.json";
import notebookTourES from "./locales/es/notebookTour.json";

// the translations
// (tip move them in a JSON file and import them,
// or even better, manage them separated from your code: https://react.i18next.com/guides/multiple-translation-files)
const resources = {
  en: {
    configurableObject: configurableObjectEN,
    common: commonEN,
    custom: customEN,
    experiments: experimentsEN,
    explainers: explainersEN,
    generative: generativeEN,
    models: modelsEN,
    datasets: datasetsEN,
    prediction: predictionEN,
    homeTour: homeTourEN,
    notebookTour: notebookTourEN,
  },
  es: {
    configurableObject: configurableObjectES,
    common: commonES,
    custom: customES,
    experiments: experimentsES,
    explainers: explainersES,
    generative: generativeES,
    models: modelsES,
    datasets: datasetsES,
    prediction: predictionES,
    homeTour: homeTourES,
    notebookTour: notebookTourES,
  },
};

i18n.use(initReactI18next).init({
  resources,

  lng: "en",
  fallbackLng: "en",

  ns: [
    "common",
    "custom",
    "configurableObject",
    "experiments",
    "explainers",
    "generative",
    "models",
    "datasets",
    "prediction",
    "homeTour",
    "notebookTour",
  ],
  defaultNS: "common",

  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
