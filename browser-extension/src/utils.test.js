/*
 * SPDX-FileCopyrightText: 2026 Legadilo contributors
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mustJwtBeRenewed } from "./utils.js";

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
