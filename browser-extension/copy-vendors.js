#!/usr/bin/env node

const fs = require("fs");

const vendorFiles = [
  "node_modules/bootstrap/dist/css/bootstrap.css",
  "node_modules/bootstrap/dist/js/bootstrap.js",
  "node_modules/bootstrap5-tags/tags.js",
];

for (const vendorFile of vendorFiles) {
  const destFileName = vendorFile.split("/").at(-1);
  fs.copyFileSync(vendorFile, `./firefox-src/vendor/${destFileName}`);
}
