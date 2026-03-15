#!/usr/bin/env node
// SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
//
// SPDX-License-Identifier: AGPL-3.0-or-later
//
// Extracts all i18n keys from HTML and JS source files, then updates every
// _locales/<locale>/messages.json:
//   - existing translations are kept as-is
//   - missing keys are added with the English text as the default value

import { readFileSync, writeFileSync, readdirSync, statSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const srcDir = join(__dirname, "..", "src");
const localesDir = join(srcDir, "_locales");

// ---------------------------------------------------------------------------
// Extraction helpers
// ---------------------------------------------------------------------------

/**
 * Parse HTML source and return a map of { key: englishText } for every
 * data-i18n and data-i18n-aria-label attribute found.
 *
 * @param {string} html
 * @returns {Record<string, string>}
 */
function extractFromHtml(html) {
  const entries = {};

  // data-i18n="key" — grab the direct text content of the element (strip child tags)
  // Handles: span, button, option, label, p, h2, title, …
  const i18nRe =
    /<[a-z][a-z0-9]*(?:[^>]*?\s)data-i18n="([^"]+)"[^>]*>([\s\S]*?)<\/[a-z][a-z0-9]*>/gi;
  for (const m of html.matchAll(i18nRe)) {
    const key = m[1];
    const text = m[2].replace(/<[^>]+>/g, "").trim();
    if (text && !entries[key]) entries[key] = text;
  }

  // data-i18n-aria-label="key" — value comes from aria-label on the same tag
  // covers both attribute orders
  const ariaRe =
    /data-i18n-aria-label="([^"]+)"[^>]*aria-label="([^"]+)"|aria-label="([^"]+)"[^>]*data-i18n-aria-label="([^"]+)"/gi;
  for (const m of html.matchAll(ariaRe)) {
    if (m[1] && m[2] && !entries[m[1]]) entries[m[1]] = m[2];
    if (m[4] && m[3] && !entries[m[4]]) entries[m[4]] = m[3];
  }

  return entries;
}

/**
 * Parse JS source and return the set of keys used in
 * chrome.i18n.getMessage("key") calls.
 *
 * @param {string} js
 * @returns {Set<string>}
 */
function extractKeysFromJs(js) {
  const keys = new Set();
  for (const m of js.matchAll(/chrome\.i18n\.getMessage\(["']([^"']+)["']/g)) {
    keys.add(m[1]);
  }
  return keys;
}

/**
 * Parse manifest.json and return the set of keys used as __MSG_key__ placeholders.
 *
 * @param {string} json
 * @returns {Set<string>}
 */
function extractKeysFromManifest(json) {
  const keys = new Set();
  for (const m of json.matchAll(/__MSG_([^_]+)__/g)) {
    keys.add(m[1]);
  }
  return keys;
}

// ---------------------------------------------------------------------------
// File scanning
// ---------------------------------------------------------------------------

const htmlFiles = ["action.html", "options.html"].map((f) => join(srcDir, f));
const jsFiles = ["action.js", "options.js"].map((f) => join(srcDir, f));
const manifestFile = join(srcDir, "manifest.json");

/** @type {Record<string, string>} collected key → English text (may stay empty for JS-only keys) */
const discovered = {};

// HTML — keys + English text
for (const file of htmlFiles) {
  const content = readFileSync(file, "utf8");
  for (const [key, text] of Object.entries(extractFromHtml(content))) {
    if (!discovered[key]) discovered[key] = text;
  }
}

// JS — keys only (no English text embedded in source)
const jsOnlyKeys = new Set();
for (const file of jsFiles) {
  for (const key of extractKeysFromJs(readFileSync(file, "utf8"))) {
    if (!discovered[key]) jsOnlyKeys.add(key);
  }
}

// manifest — keys only
for (const key of extractKeysFromManifest(readFileSync(manifestFile, "utf8"))) {
  if (!discovered[key]) jsOnlyKeys.add(key);
}

// ---------------------------------------------------------------------------
// Load existing English messages as authoritative source for JS-only keys
// ---------------------------------------------------------------------------

const enPath = join(localesDir, "en", "messages.json");
/** @type {Record<string, { message: string }>} */
const existingEn = JSON.parse(readFileSync(enPath, "utf8"));

// For JS-only keys, fall back to the existing English entry (or empty string)
for (const key of jsOnlyKeys) {
  discovered[key] = existingEn[key]?.message ?? key;
}

console.log(`Discovered ${Object.keys(discovered).length} i18n keys total.`);

// ---------------------------------------------------------------------------
// Update locale files
// ---------------------------------------------------------------------------

const localeDirs = readdirSync(localesDir).filter((d) =>
  statSync(join(localesDir, d)).isDirectory(),
);

for (const locale of localeDirs) {
  const filePath = join(localesDir, locale, "messages.json");
  /** @type {Record<string, { message: string }>} */
  let existing = {};
  try {
    existing = JSON.parse(readFileSync(filePath, "utf8"));
  } catch {
    // file doesn't exist yet — start empty
  }

  let added = 0;
  let updated = 0;
  for (const [key, englishText] of Object.entries(discovered)) {
    if (!existing[key]) {
      existing[key] = { message: englishText };
      added++;
    } else if (locale === "en" && existing[key].message !== englishText && englishText !== "") {
      existing[key] = { message: englishText };
      updated++;
    }
  }

  let deleted = 0;
  for (const key of Object.keys(existing)) {
    if (!discovered[key]) {
      delete existing[key];
      deleted++;
    }
  }

  writeFileSync(filePath, JSON.stringify(existing, null, 2) + "\n", "utf8");
  console.log(
    `[${locale}] ${added} key(s) added, ${updated} key(s) updated, ${deleted} key(s) deleted, ${Object.keys(existing).length} total → ${filePath}`,
  );
}
