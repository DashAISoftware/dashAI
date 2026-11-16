import { tours, TOUR_KEYS } from ".";
import en from "../../utils/i18n/locales/en/pluginsTour.json";
import es from "../../utils/i18n/locales/es/pluginsTour.json";
import pt from "../../utils/i18n/locales/pt/pluginsTour.json";
import de from "../../utils/i18n/locales/de/pluginsTour.json";
import zh from "../../utils/i18n/locales/zh/pluginsTour.json";

const locales = { en, es, pt, de, zh };

describe.each([TOUR_KEYS.PLUGINS, TOUR_KEYS.PLUGIN_SAMPLE])(
  "%s tour",
  (tourKey) => {
    const { steps } = tours[tourKey];

    it("targets body or a data-tour anchor on every step", () => {
      expect(steps.length).toBeGreaterThan(0);
      steps.forEach((step) => {
        expect(step.target).toMatch(/^(body|\[data-tour="[\w-]+"\])$/);
      });
    });

    it.each(Object.keys(locales))("has every step text in %s", (lang) => {
      steps.forEach((step) => {
        const [ns, key] = step.content.props.i18nKey.split(":");
        expect(ns).toBe("pluginsTour");
        expect(locales[lang][key]).toEqual(expect.any(String));
      });
    });
  },
);
