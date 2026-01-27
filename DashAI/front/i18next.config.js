const { defineConfig } = require("i18next-cli");

/** @type {import('i18next-cli').I18nextToolkitConfig} */
module.exports = defineConfig({
  locales: ["en", "es"],
  extract: {
    input: "src/**/*.{js,jsx,ts,tsx}",
    output: "src/utils/i18n/locales/{{language}}/{{namespace}}.json",
  },
});
