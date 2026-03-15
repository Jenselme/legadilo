/*
 * SPDX-FileCopyrightText: 2026 Legadilo contributors
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  DEFAULT_OPTIONS,
  deleteArticle,
  deleteFeed,
  listArticles,
  listEnabledFeeds,
  loadOptions,
  saveArticle,
  storeOptions,
  subscribeToFeed,
  testCredentials,
  updateArticle,
  updateFeed,
} from "./legadilo.js";

/**
 * Builds a minimal JWT whose `exp` is set far in the future so mustJwtBeRenewed returns false.
 */
function makeFreshJwt() {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const exp = Math.floor(Date.now() / 1000) + 60 * 60; // 1 hour from now
  const payload = btoa(JSON.stringify({ exp }))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
  return `${header}.${payload}.fakesig`;
}

/**
 * Returns a mock Options object with a valid (non-expiring) access token.
 *
 * @param {Partial<import('./types.js').Options>} [overrides]
 */
function makeOptions(overrides = {}) {
  return {
    instanceUrl: "https://example.com",
    userEmail: "user@example.com",
    tokenId: "tid",
    tokenSecret: "tsecret",
    accessToken: makeFreshJwt(),
    ...overrides,
  };
}

/**
 * Returns a mock Response object.
 *
 * @param {{ status?: number; statusText?: string; ok?: boolean; body?: unknown; rejectJson?: boolean }} [opts]
 * @returns {Response}
 */
function mockResponse({
  status = 200,
  statusText = "OK",
  ok = true,
  body = {},
  rejectJson = false,
} = {}) {
  return /** @type {Response} */ (
    /** @type {unknown} */ ({
      status,
      statusText,
      ok,
      json: rejectJson
        ? () => Promise.reject(new SyntaxError("not json"))
        : () => Promise.resolve(body),
    })
  );
}

describe("testCredentials", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns true on success", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse({ status: 200 }));

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

  it("returns false when the server returns a non-200 status", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse({ status: 401 }));

    const result = await testCredentials({
      instanceUrl: "https://example.com",
      userEmail: "test@example.com",
      tokenId: "id",
      tokenSecret: "secret",
    });

    expect(result).toBe(false);
  });

  it("returns false on network error", async () => {
    vi.mocked(fetch).mockRejectedValue(new Error("Network error"));

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

describe("loadOptions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls chrome.storage.local.get with DEFAULT_OPTIONS and returns the result", async () => {
    const stored = { ...DEFAULT_OPTIONS, instanceUrl: "https://my.instance" };
    vi.mocked(chrome.storage.local.get).mockResolvedValue(/** @type {any} */ (stored));

    const result = await loadOptions();

    expect(chrome.storage.local.get).toHaveBeenCalledWith(DEFAULT_OPTIONS);
    expect(result).toEqual(stored);
  });
});

describe("storeOptions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("stores provided credentials and resets the access token", async () => {
    vi.mocked(chrome.storage.local.set).mockResolvedValue(undefined);

    await storeOptions({
      instanceUrl: "https://example.com",
      userEmail: "user@example.com",
      tokenId: "tid",
      tokenSecret: "tsecret",
    });

    expect(chrome.storage.local.set).toHaveBeenCalledWith({
      instanceUrl: "https://example.com",
      userEmail: "user@example.com",
      tokenId: "tid",
      tokenSecret: "tsecret",
      accessToken: "",
    });
  });
});

describe("saveArticle", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(chrome.storage.local.get).mockResolvedValue(/** @type {any} */ (makeOptions()));
    vi.mocked(chrome.storage.local.set).mockResolvedValue(undefined);
  });

  it("throws when the URL is not http/https", async () => {
    await expect(
      saveArticle({
        url: "ftp://example.com/file",
        title: "title",
        content: "content",
        contentType: "text/html",
        language: "en",
        mustExtractContent: false,
      }),
    ).rejects.toThrow("Invalid url");
  });

  it("sends full article data when title and content are present", async () => {
    const article = { id: 1, title: "My Article" };
    vi.mocked(fetch).mockResolvedValue(mockResponse({ body: article }));

    const result = await saveArticle({
      url: "https://example.com/article",
      title: "My Article",
      content: "<p>text</p>",
      contentType: "text/html",
      language: "en",
      mustExtractContent: false,
    });

    expect(result).toEqual(article);
    const body = JSON.parse(/** @type {string} */ (vi.mocked(fetch).mock.calls[0]?.[1]?.body));
    expect(body).toMatchObject({
      url: "https://example.com/article",
      title: "My Article",
      content: "<p>text</p>",
    });
  });

  it("sends only the URL when title is missing", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse({ body: { id: 2 } }));

    await saveArticle({
      url: "https://example.com/article",
      title: "",
      content: "<p>text</p>",
      contentType: "text/html",
      language: "en",
      mustExtractContent: false,
    });

    const body = JSON.parse(/** @type {string} */ (vi.mocked(fetch).mock.calls[0]?.[1]?.body));
    expect(body).toEqual({ url: "https://example.com/article" });
  });

  it("falls back to URL-only on a 400 Bad Request error", async () => {
    const article = { id: 3 };
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        mockResponse({ status: 400, statusText: "Bad Request", ok: false, rejectJson: true }),
      )
      .mockResolvedValueOnce(mockResponse({ body: article }));

    const result = await saveArticle({
      url: "https://example.com/article",
      title: "Title",
      content: "<p>very long</p>",
      contentType: "text/html",
      language: "en",
      mustExtractContent: false,
    });

    expect(result).toEqual(article);
    expect(fetch).toHaveBeenCalledTimes(2);
    const fallbackBody = JSON.parse(
      /** @type {string} */ (vi.mocked(fetch).mock.calls[1]?.[1]?.body),
    );
    expect(fallbackBody).toEqual({ url: "https://example.com/article" });
  });
});

describe("updateArticle", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(chrome.storage.local.get).mockResolvedValue(/** @type {any} */ (makeOptions()));
    vi.mocked(chrome.storage.local.set).mockResolvedValue(undefined);
  });

  it("sends a PATCH request with the mapped payload", async () => {
    const updated = { id: 10, title: "Updated" };
    vi.mocked(fetch).mockResolvedValue(mockResponse({ body: updated }));

    const result = await updateArticle(10, {
      title: "Updated",
      tags: ["news"],
      group: "2",
      readAt: "2026-01-01T00:00:00Z",
      isFavorite: true,
      isForLater: false,
      readingTime: 5,
    });

    expect(result).toEqual(updated);
    const [url, opts] = /** @type {[string, RequestInit]} */ (vi.mocked(fetch).mock.calls[0]);
    expect(url).toContain("/api/reading/articles/10/");
    expect(opts.method).toBe("PATCH");
    const body = JSON.parse(/** @type {string} */ (opts.body));
    expect(body).toMatchObject({ title: "Updated", group_id: "2", reading_time: 5 });
  });
});

describe("deleteArticle", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(chrome.storage.local.get).mockResolvedValue(/** @type {any} */ (makeOptions()));
    vi.mocked(chrome.storage.local.set).mockResolvedValue(undefined);
  });

  it("sends a DELETE request and returns an empty object", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse({ status: 204 }));

    const result = await deleteArticle(42);

    expect(result).toEqual({});
    const [url, opts] = /** @type {[string, RequestInit]} */ (vi.mocked(fetch).mock.calls[0]);
    expect(url).toContain("/api/reading/articles/42/");
    expect(opts.method).toBe("DELETE");
  });
});

describe("listArticles", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(chrome.storage.local.get).mockResolvedValue(/** @type {any} */ (makeOptions()));
    vi.mocked(chrome.storage.local.set).mockResolvedValue(undefined);
  });

  it("fetches all articles when no URLs are provided", async () => {
    const response = { count: 1, items: [{ id: 1 }] };
    vi.mocked(fetch).mockResolvedValue(mockResponse({ body: response }));

    const result = await listArticles({});

    expect(result).toEqual(response);
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(vi.mocked(fetch).mock.calls[0][0]).toContain("/api/reading/articles/");
  });

  it("queries each URL individually and merges the results", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(mockResponse({ body: { count: 1, items: [{ id: 1 }] } }))
      .mockResolvedValueOnce(mockResponse({ body: { count: 1, items: [{ id: 2 }] } }));

    const result = await listArticles({
      articleUrls: ["https://example.com/a", "https://example.com/b"],
    });

    expect(result.count).toBe(2);
    expect(result.items).toHaveLength(2);
    expect(result.items[0].id).toBe(1);
    expect(result.items[1].id).toBe(2);
  });

  it("encodes the article URL in the query string", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse({ body: { count: 0, items: [] } }));

    await listArticles({ articleUrls: ["https://example.com/path?q=1"] });

    const calledUrl = vi.mocked(fetch).mock.calls[0][0];
    expect(calledUrl).toContain(encodeURIComponent("https://example.com/path?q=1"));
  });
});

describe("subscribeToFeed", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(chrome.storage.local.get).mockResolvedValue(/** @type {any} */ (makeOptions()));
    vi.mocked(chrome.storage.local.set).mockResolvedValue(undefined);
  });

  it("sends a POST request with the feed URL", async () => {
    const feed = { id: 5, feed_url: "https://example.com/feed.xml" };
    vi.mocked(fetch).mockResolvedValue(mockResponse({ body: feed }));

    const result = await subscribeToFeed("https://example.com/feed.xml");

    expect(result).toEqual(feed);
    const [url, opts] = /** @type {[string, RequestInit]} */ (vi.mocked(fetch).mock.calls[0]);
    expect(url).toContain("/api/feeds/");
    expect(opts.method).toBe("POST");
    expect(JSON.parse(/** @type {string} */ (opts.body))).toEqual({
      feed_url: "https://example.com/feed.xml",
    });
  });
});

describe("listEnabledFeeds", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(chrome.storage.local.get).mockResolvedValue(/** @type {any} */ (makeOptions()));
    vi.mocked(chrome.storage.local.set).mockResolvedValue(undefined);
  });

  it("fetches all feeds when no feed URLs are provided", async () => {
    const response = { items: [{ id: 1 }] };
    vi.mocked(fetch).mockResolvedValue(mockResponse({ body: response }));

    const result = await listEnabledFeeds({});

    expect(result).toEqual(response);
    expect(vi.mocked(fetch).mock.calls[0][0]).toContain("/api/feeds/");
  });

  it("builds a query string with enabled=true when feed URLs are provided", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse({ body: { items: [] } }));

    await listEnabledFeeds({ feedUrls: ["https://example.com/feed.xml"] });

    const calledUrl = vi.mocked(fetch).mock.calls[0][0];
    expect(calledUrl).toContain("enabled=true");
    expect(calledUrl).toContain(encodeURIComponent("https://example.com/feed.xml"));
  });
});

describe("deleteFeed", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(chrome.storage.local.get).mockResolvedValue(/** @type {any} */ (makeOptions()));
    vi.mocked(chrome.storage.local.set).mockResolvedValue(undefined);
  });

  it("sends a DELETE request to the correct feed endpoint", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse({ status: 204 }));

    const result = await deleteFeed(7);

    expect(result).toEqual({});
    const [url, opts] = /** @type {[string, RequestInit]} */ (vi.mocked(fetch).mock.calls[0]);
    expect(url).toContain("/api/feeds/7/");
    expect(opts.method).toBe("DELETE");
  });
});

describe("updateFeed", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(chrome.storage.local.get).mockResolvedValue(/** @type {any} */ (makeOptions()));
    vi.mocked(chrome.storage.local.set).mockResolvedValue(undefined);
  });

  it("sends a PATCH request with the mapped feed payload", async () => {
    const updatedFeed = { id: 3, refresh_delay: 60 };
    vi.mocked(fetch).mockResolvedValue(mockResponse({ body: updatedFeed }));

    const result = await updateFeed(3, {
      category: "1",
      tags: ["tech"],
      refreshDelay: "DAILY_AT_NOON",
      articleRetentionTime: 30,
      disabledAt: null,
      disabledReason: "",
    });

    expect(result).toEqual(updatedFeed);
    const [url, opts] = /** @type {[string, RequestInit]} */ (vi.mocked(fetch).mock.calls[0]);
    expect(url).toContain("/api/feeds/3/");
    expect(opts.method).toBe("PATCH");
    const body = JSON.parse(/** @type {string} */ (opts.body));
    expect(body).toMatchObject({
      category_id: "1",
      refresh_delay: "DAILY_AT_NOON",
      article_retention_time: 30,
    });
  });
});

describe("doFetch error handling", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(chrome.storage.local.get).mockResolvedValue(/** @type {any} */ (makeOptions()));
    vi.mocked(chrome.storage.local.set).mockResolvedValue(undefined);
  });

  it("throws with status and detail when response is not ok and body has a detail field", async () => {
    vi.mocked(fetch).mockResolvedValue(
      mockResponse({ status: 422, ok: false, body: { detail: "Unprocessable entity" } }),
    );

    await expect(deleteArticle(1)).rejects.toThrow("Unprocessable entity");
  });

  it("throws with status text only when response is not ok and body is not JSON", async () => {
    vi.mocked(fetch).mockResolvedValue(mockResponse({ status: 500, ok: false, rejectJson: true }));

    await expect(deleteArticle(1)).rejects.toThrow("Response status: 500");
  });
});
