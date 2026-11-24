const react = require("eslint-plugin-react");
const reactHooks = require("eslint-plugin-react-hooks");
const globals = require("globals");
const tsParser = require("@typescript-eslint/parser");

const correctness = {
  "no-undef": "error",
  "no-dupe-keys": "error",
  "no-dupe-args": "error",
  "no-dupe-else-if": "error",
  "no-duplicate-case": "error",
  "no-unreachable": "error",
  "no-self-assign": "error",
  "no-self-compare": "error",
  "no-constant-condition": "error",
  "no-cond-assign": "error",
  "no-unsafe-optional-chaining": "error",
  "no-unsafe-negation": "error",
  "no-fallthrough": "error",
  "no-useless-catch": "error",
  "no-async-promise-executor": "error",
  "no-prototype-builtins": "error",
  "use-isnan": "error",
  "valid-typeof": "error",
  "no-import-assign": "error",
  "no-const-assign": "error",
  "no-redeclare": "error",
  "no-shadow-restricted-names": "error",
  "no-sparse-arrays": "error",
  "getter-return": "error",
  "no-debugger": "error",
  "no-empty": "warn",
  "no-console": ["warn", { allow: ["error", "warn"] }],
  "no-unused-vars": [
    "error",
    {
      args: "none",
      caughtErrors: "none",
      ignoreRestSiblings: true,
      varsIgnorePattern: "^_",
    },
  ],
};

module.exports = [
  {
    ignores: [
      "build/**",
      "node_modules/**",
      ".yarn/**",
      "*.config.*",
      "src/components/datasets/SelectDataloaderStep.jsx",
    ],
  },
  {
    files: ["src/**/*.{js,jsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: { ...globals.browser, ...globals.es2021 },
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    plugins: { react, "react-hooks": reactHooks },
    settings: { react: { version: "detect" } },
    rules: {
      ...correctness,
      "react/jsx-key": "error",
      "react/jsx-no-undef": "error",
      "react/jsx-uses-vars": "error",
      "react/jsx-uses-react": "error",
      "react/jsx-no-duplicate-props": "error",
      "react/no-direct-mutation-state": "error",
      "react/no-unknown-property": "error",
      "react/no-children-prop": "error",
      "react/jsx-no-target-blank": "error",
      "react/display-name": "error",
      "react/no-unstable-nested-components": "warn",
      "react/no-array-index-key": "warn",
      "react/no-unescaped-entities": "warn",
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
    },
  },
  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      parser: tsParser,
      ecmaVersion: 2022,
      sourceType: "module",
      globals: { ...globals.browser, ...globals.es2021 },
    },
    rules: {
      "no-dupe-keys": "error",
      "no-unreachable": "error",
      "no-debugger": "error",
      "no-console": ["warn", { allow: ["error", "warn"] }],
    },
  },
];
