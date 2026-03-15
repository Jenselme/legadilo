// SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
//
// SPDX-License-Identifier: AGPL-3.0-or-later

import { describe, expect, it, vi } from "vitest";

vi.mock("./vendor/tags.js", () => ({ default: class Tags {} }));
vi.mock("./vendor/Readability.js", () => ({ default: class Readability {} }));
vi.mock("./i18n.js", () => ({ applyI18n: vi.fn() }));
vi.mock("./legadilo.js", () => ({
  listArticles: vi.fn(),
  listEnabledFeeds: vi.fn(),
  loadOptions: vi.fn(),
}));

import { __test__ } from "./action.js";
const {
  buildFullUrl,
  getCanonicalUrl,
  getFeedHref,
  getFeedNodes,
  getPageUrlFromTab,
  tagsToAutocompleteItems,
} = __test__;

describe("getPageUrlFromTab", () => {
  it("returns the tab url for a normal http URL", () => {
    expect(
      getPageUrlFromTab(/** @type {chrome.tabs.Tab} */ ({ url: "https://example.com/page" })),
    ).toBe("https://example.com/page");
  });

  it("returns empty string when tab.url is undefined", () => {
    expect(getPageUrlFromTab(/** @type {chrome.tabs.Tab} */ ({}))).toBe("");
  });

  it("extracts the url query param from an about: URL", () => {
    expect(
      getPageUrlFromTab(
        /** @type {chrome.tabs.Tab} */ ({
          url: "about:reader?url=https%3A%2F%2Fexample.com%2Farticle",
        }),
      ),
    ).toBe("https://example.com/article");
  });

  it("returns empty string when about: URL has no url param", () => {
    expect(getPageUrlFromTab(/** @type {chrome.tabs.Tab} */ ({ url: "about:blank" }))).toBe("");
  });
});

describe("buildFullUrl", () => {
  const tab = /** @type {chrome.tabs.Tab} */ ({ url: "https://example.com/some/page" });

  it("returns absolute https URLs unchanged", () => {
    expect(buildFullUrl(tab, "https://cdn.example.com/feed.xml")).toBe(
      "https://cdn.example.com/feed.xml",
    );
  });

  it("returns absolute http URLs unchanged", () => {
    expect(buildFullUrl(tab, "http://cdn.example.com/feed.xml")).toBe(
      "http://cdn.example.com/feed.xml",
    );
  });

  it("prepends the page protocol to a protocol-relative URL", () => {
    expect(buildFullUrl(tab, "//cdn.example.com/feed.xml")).toBe(
      "https://cdn.example.com/feed.xml",
    );
  });

  it("prepends the origin to a root-relative URL", () => {
    expect(buildFullUrl(tab, "/feeds/main.xml")).toBe("https://example.com/feeds/main.xml");
  });
});

describe("tagsToAutocompleteItems", () => {
  it("maps an empty array to an empty array", () => {
    expect(tagsToAutocompleteItems([])).toEqual([]);
  });

  it("maps tag fields to autocomplete item fields", () => {
    const tags = [
      { slug: "js", title: "JavaScript", hierarchy: [] },
      { slug: "ts", title: "TypeScript", hierarchy: [] },
    ];
    expect(tagsToAutocompleteItems(tags)).toEqual([
      { value: "js", label: "JavaScript", hierarchy: [] },
      { value: "ts", label: "TypeScript", hierarchy: [] },
    ]);
  });

  it("preserves hierarchy on each item", () => {
    const parent = { slug: "web", title: "Web", hierarchy: [] };
    const child = { slug: "js", title: "JavaScript", hierarchy: [parent] };
    expect(tagsToAutocompleteItems([child])).toEqual([
      { value: "js", label: "JavaScript", hierarchy: [parent] },
    ]);
  });
});

describe("getFeedNodes", () => {
  it("returns empty array for text/plain content", () => {
    expect(getFeedNodes("<html></html>", "text/plain")).toEqual([]);
  });

  it("returns RSS feed link elements", () => {
    const pageContent = `<html><head>
      <link rel="alternate" type="application/rss+xml" href="/feed.rss" />
    </head></html>`;
    const nodes = getFeedNodes(pageContent, "text/html");
    expect(nodes).toHaveLength(1);
    expect(nodes[0].getAttribute("href")).toBe("/feed.rss");
  });

  it("returns Atom feed link elements", () => {
    const pageContent = `<html><head>
      <link rel="alternate" type="application/atom+xml" href="/feed.atom" />
    </head></html>`;
    const nodes = getFeedNodes(pageContent, "text/html");
    expect(nodes).toHaveLength(1);
    expect(nodes[0].getAttribute("href")).toBe("/feed.atom");
  });

  it("returns both RSS and Atom feed link elements", () => {
    const pageContent = `<html><head>
      <link rel="alternate" type="application/rss+xml" href="/feed.rss" />
      <link rel="alternate" type="application/atom+xml" href="/feed.atom" />
    </head></html>`;
    expect(getFeedNodes(pageContent, "text/html")).toHaveLength(2);
  });

  it("returns empty array when no feed links are present", () => {
    const pageContent = `<html><head><title>No feeds</title></head></html>`;
    expect(getFeedNodes(pageContent, "text/html")).toHaveLength(0);
  });
});

describe("getCanonicalUrl", () => {
  const tab = /** @type {chrome.tabs.Tab} */ ({ url: "https://example.com/page" });

  it("returns null for text/plain content", () => {
    expect(
      getCanonicalUrl(tab, /** @type {any} */ ({ pageContent: "", contentType: "text/plain" })),
    ).toBeNull();
  });

  it("returns null when there is no canonical link", () => {
    const data = /** @type {any} */ ({
      pageContent: "<html><head></head></html>",
      contentType: "text/html",
    });
    expect(getCanonicalUrl(tab, data)).toBeNull();
  });

  it("returns the canonical URL when present as an absolute URL", () => {
    const data = /** @type {any} */ ({
      pageContent: `<html><head><link rel="canonical" href="https://canonical.example.com/article" /></head></html>`,
      contentType: "text/html",
    });
    expect(getCanonicalUrl(tab, data)).toBe("https://canonical.example.com/article");
  });

  it("resolves a root-relative canonical href against the tab origin", () => {
    const data = /** @type {any} */ ({
      pageContent: `<html><head><link rel="canonical" href="/article/123" /></head></html>`,
      contentType: "text/html",
    });
    expect(getCanonicalUrl(tab, data)).toBe("https://example.com/article/123");
  });
});

describe("getFeedHref", () => {
  const tab = /** @type {chrome.tabs.Tab} */ ({ url: "https://example.com/page" });

  it("returns the absolute href as-is", () => {
    const node = document.createElement("link");
    node.setAttribute("href", "https://feeds.example.com/rss.xml");
    expect(getFeedHref(tab, node)).toBe("https://feeds.example.com/rss.xml");
  });

  it("resolves a root-relative href against the tab origin", () => {
    const node = document.createElement("link");
    node.setAttribute("href", "/feed.rss");
    expect(getFeedHref(tab, node)).toBe("https://example.com/feed.rss");
  });

  it("returns the tab origin when href is empty", () => {
    const node = document.createElement("link");
    expect(getFeedHref(tab, node)).toBe("https://example.com");
  });
});
