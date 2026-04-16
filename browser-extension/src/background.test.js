// SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
//
// SPDX-License-Identifier: AGPL-3.0-or-later

import { describe, expect, it, vi } from "vitest";

vi.mock("./legadilo.js", () => ({
  loadOptions: vi.fn(),
  saveArticle: vi.fn(),
  updateArticle: vi.fn(),
  deleteArticle: vi.fn(),
  subscribeToFeed: vi.fn(),
  updateFeed: vi.fn(),
  deleteFeed: vi.fn(),
}));

import { __test__ } from "./background.js";
const { checkIsBrowserInternalUrl } = __test__;

describe("checkIsBrowserInternalUrl", () => {
  it("returns false for a normal https URL", () => {
    expect(checkIsBrowserInternalUrl("https://example.com/article")).toBe(false);
  });

  it("returns true for chrome:// URLs", () => {
    expect(checkIsBrowserInternalUrl("chrome://extensions/")).toBe(true);
  });

  it("returns true for moz-extension:// URLs", () => {
    expect(checkIsBrowserInternalUrl("moz-extension://some-id/popup.html")).toBe(true);
  });

  it("returns true for about:blank", () => {
    expect(checkIsBrowserInternalUrl("about:blank")).toBe(true);
  });

  it("returns true for other about: URLs", () => {
    expect(checkIsBrowserInternalUrl("about:newtab")).toBe(true);
  });

  it("returns false for about:reader? URLs (reading mode)", () => {
    expect(checkIsBrowserInternalUrl("about:reader?url=https%3A%2F%2Fexample.com%2Farticle")).toBe(
      false,
    );
  });
});
