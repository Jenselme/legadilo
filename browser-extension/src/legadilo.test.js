/*
 * SPDX-FileCopyrightText: 2026 Legadilo contributors
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { testCredentials } from "./legadilo.js";

describe("legadilo.js", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("testCredentials returns true on success", async () => {
    // Mock fetch response
    fetch.mockResolvedValue({
      status: 200,
      ok: true,
      json: () => Promise.resolve({}),
    });

    const result = await testCredentials({
      instanceUrl: "https://example.com",
      userEmail: "test@example.com",
      tokenId: "id",
      tokenSecret: "secret",
    });

    expect(result).toBe(true);
    expect(fetch).toHaveBeenCalledWith(
      "https://example.com/api/users/tokens/",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("testCredentials returns false on error", async () => {
    fetch.mockRejectedValue(new Error("Network error"));

    const result = await testCredentials({
      instanceUrl: "https://example.com",
      userEmail: "test@example.com",
      tokenId: "id",
      tokenSecret: "secret",
    });

    expect(result).toBe(false);
    expect(console.error).toHaveBeenCalled();
  });
});
