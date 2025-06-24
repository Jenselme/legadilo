#!/usr/bin/env node

// SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
//
// SPDX-License-Identifier: AGPL-3.0-or-later

const fs = require("fs");

const vendorFiles = [
  "node_modules/bootstrap/dist/css/bootstrap.css",
  "node_modules/bootstrap/dist/js/bootstrap.js",
  "node_modules/bootstrap5-tags/tags.js",
];

for (const vendorFile of vendorFiles) {
  const destFileName = vendorFile.split("/").at(-1);
  fs.copyFileSync(vendorFile, `./src/vendor/${destFileName}`);
}
