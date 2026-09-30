// Import order matters: the localStorage polyfill must be installed before
// the i18n instance boots (it reads the persisted language on import).
import "./localStoragePolyfill";
import "@testing-library/jest-dom/vitest";
import "../i18n";
