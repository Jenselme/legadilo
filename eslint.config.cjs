const globals = require("globals");
const pluginJs = require("@eslint/js");

module.exports = [
  {
    languageOptions: { globals: { ...globals.browser, htmx: true, bootstrap: true } },
  },
  {
    files: ["browser-extension/**/*.js"],
    languageOptions: { globals: { browser: true, chrome: true } },
  },
  {
    files: ["browser-extension/*.js"],
    languageOptions: { globals: { ...globals.node } },
  },
  pluginJs.configs.recommended,
];
