import js from "@eslint/js";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";

export default [
  {
    ignores: ["dist/**", "coverage/**", "node_modules/**"],
  },
  js.configs.recommended,
  {
    files: ["**/*.{js,jsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: {
        ...globals.browser,
        ...globals.es2021,
      },
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
    },
    settings: { react: { version: "detect" } },
    plugins: {
      react,
      "react-hooks": reactHooks,
    },
    rules: {
      ...react.configs.flat.recommended.rules,
      ...react.configs.flat["jsx-runtime"].rules,
      ...reactHooks.configs.recommended.rules,
      // No PropTypes: components receive plain JS objects, validated by tests.
      "react/prop-types": "off",
      "no-unused-vars": ["error", { varsIgnorePattern: "^_" }],
    },
  },
  {
    // Node-only files (config, scripts).
    files: ["*.config.js", "vite.config.js"],
    languageOptions: { globals: { ...globals.node } },
  },
  {
    files: ["src/test/**/*.{js,jsx}"],
    languageOptions: {
      globals: { ...globals.vitest, ...globals.node },
    },
  },
];
