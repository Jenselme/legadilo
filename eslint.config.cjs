const globals = require("globals");
const pluginJs = require("@eslint/js");

module.exports = [
  { languageOptions: { globals: { ...globals.browser, htmx: true, bootstrap: true } } },
  pluginJs.configs.recommended,
];
