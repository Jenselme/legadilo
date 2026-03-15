/*
 * SPDX-FileCopyrightText: 2026 Legadilo contributors
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getErrorMessage, html, mergeUrlFragments, mustJwtBeRenewed } from "./utils.js";

/**
 * @param {{ exp?: number; sub?: string; }} payload
 */
function makeJwt(payload) {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  // Convert to URL-safe base64.
  const encodedPayload = btoa(JSON.stringify(payload))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
  return `${header}.${encodedPayload}.fakesignature`;
}

describe("isTokenExpiredOrExpiringSoon", () => {
  const NOW = new Date("2026-01-01T12:00:00Z").getTime();

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(NOW);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("should return false for a token expiring after the buffer", () => {
    const exp = Math.floor((NOW + 6 * 60 * 1000) / 1000); // expires in 6 minutes
    expect(mustJwtBeRenewed(makeJwt({ exp }))).toBe(false);
  });

  it("should return true for a token expiring within the buffer", () => {
    const exp = Math.floor((NOW + 4 * 60 * 1000) / 1000); // expires in 4 minutes
    expect(mustJwtBeRenewed(makeJwt({ exp }))).toBe(true);
  });

  it("should return true for an already-expired token", () => {
    const exp = Math.floor((NOW - 60 * 1000) / 1000); // expired 1 minute ago
    expect(mustJwtBeRenewed(makeJwt({ exp }))).toBe(true);
  });

  it.each([
    { token: "invalid", label: "plain invalid string" },
    { token: "not.a.valid.jwt.at.all", label: "too many segments" },
    { token: makeJwt({ sub: "user" }), label: "missing exp claim" },
  ])("should return true for an invalid or missing token: $label", ({ token }) => {
    expect(mustJwtBeRenewed(token)).toBe(true);
  });
});

describe("html", () => {
  it("should return a string for a plain template with no interpolations", () => {
    expect(html`<p>Hello</p>`.toString()).toBe("<p>Hello</p>");
  });

  it("should interpolate a plain string value unescaped when safe", () => {
    const value = "World";
    expect(html`<p>${value}</p>`.toString()).toBe("<p>World</p>");
  });

  it("should escape & in interpolated values", () => {
    const value = "foo & bar";
    expect(html`<p>${value}</p>`.toString()).toBe("<p>foo &amp; bar</p>");
  });

  it("should escape < and > in interpolated values", () => {
    const value = "<script>";
    expect(html`<p>${value}</p>`.toString()).toBe("<p>&lt;script&gt;</p>");
  });

  it("should escape double quotes in interpolated values", () => {
    const value = 'say "hi"';
    expect(html`<p>${value}</p>`.toString()).toBe("<p>say &quot;hi&quot;</p>");
  });

  it("should escape single quotes in interpolated values", () => {
    const value = "it's";
    expect(html`<p>${value}</p>`.toString()).toBe("<p>it&#x27;s</p>");
  });

  it("should not double-escape a nested html`` value", () => {
    const inner = html`<strong>bold</strong>`;
    expect(html`<p>${inner}</p>`.toString()).toBe("<p><strong>bold</strong></p>");
  });

  it("should coerce numbers to strings", () => {
    expect(html`<span>${42}</span>`.toString()).toBe("<span>42</span>");
  });

  it("should coerce null to an empty string", () => {
    expect(html`<span>${null}</span>`.toString()).toBe("<span></span>");
  });

  it("should coerce undefined to an empty string", () => {
    expect(html`<span>${undefined}</span>`.toString()).toBe("<span></span>");
  });

  it("should handle multiple interpolations in one template", () => {
    const text = "<item>";
    expect(html`${text}${text}`.toString()).toBe("&lt;item&gt;&lt;item&gt;");
  });

  it("should produce a value that can be used as innerHTML", () => {
    // @ts-ignore
    document.body.innerHTML = html`<p id="test">${"<b>safe</b>"}</p>`;
    const p = document.getElementById("test");
    expect(p?.textContent).toBe("<b>safe</b>");
  });
});

describe("getErrorMessage", () => {
  it("should return the error message when given an Error instance", () => {
    expect(getErrorMessage(new Error("something went wrong"))).toBe("something went wrong");
  });

  it("should return the fallback when err is not an Error and a fallback is provided", () => {
    expect(getErrorMessage("raw string", "fallback message")).toBe("fallback message");
  });

  it("should return String(err) when err is not an Error and no fallback is provided", () => {
    expect(getErrorMessage(42)).toBe("42");
  });

  it("should return String(err) for a plain object with no fallback", () => {
    expect(getErrorMessage({ code: 500 })).toBe("[object Object]");
  });
});

describe("mergeUrlFragments", () => {
  it("should join two fragments with a single slash", () => {
    expect(mergeUrlFragments("https://example.com", "api")).toBe("https://example.com/api");
  });

  it("should remove trailing slash from the first fragment", () => {
    expect(mergeUrlFragments("https://example.com/", "api")).toBe("https://example.com/api");
  });

  it("should remove leading slash from the last fragment", () => {
    expect(mergeUrlFragments("https://example.com", "/api")).toBe("https://example.com/api");
  });

  it("should remove both trailing and leading slashes between two fragments", () => {
    expect(mergeUrlFragments("https://example.com/", "/api")).toBe("https://example.com/api");
  });

  it("should preserve a trailing slash on the last fragment", () => {
    expect(mergeUrlFragments("https://example.com/", "/api/")).toBe("https://example.com/api/");
  });
});
