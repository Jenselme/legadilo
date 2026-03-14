// SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
//
// SPDX-License-Identifier: AGPL-3.0-or-later

/** @typedef {import('./types.js').Tag} Tag */
/** @typedef {import('./types.js').Category} Category */
/** @typedef {import('./types.js').Article} Article */
/** @typedef {import('./types.js').Feed} Feed */
/** @typedef {import('./types.js').Options} Options */
/** @typedef {import('./types.js').SaveArticlePayload} SaveArticlePayload */
/** @typedef {import('./types.js').UpdateArticlePayload} UpdateArticlePayload */

import { mergeUrlFragments, mustJwtBeRenewed } from "./utils.js";

/** @typedef {import('./types.js').UpdateFeedPayload} UpdateFeedPayload */

const DEFAULT_LEGADILO_URL = "https://www.legadilo.eu";
export const DEFAULT_OPTIONS = {
  instanceUrl: DEFAULT_LEGADILO_URL,
  userEmail: "",
  tokenId: "",
  tokenSecret: "",
  accessToken: "",
};

/**
 * @param {{instanceUrl: string, userEmail: string, tokenId: string, tokenSecret: string}} params
 * @returns {Promise<boolean>}
 */
export const testCredentials = async ({ instanceUrl, userEmail, tokenId, tokenSecret }) => {
  try {
    const resp = await fetch(mergeUrlFragments(instanceUrl, "/api/users/tokens/"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: userEmail,
        application_token_uuid: tokenId,
        application_token_secret: tokenSecret,
      }),
    });
    await resp.json();
    return resp.status === 200;
  } catch (error) {
    console.error(error);
    return false;
  }
};

/**
 * @param {SaveArticlePayload} params
 * @returns {Promise<Article>}
 */
export const saveArticle = async ({
  url,
  title,
  content,
  contentType,
  language,
  mustExtractContent,
}) => {
  if (!/^https?:\/\//.test(url)) {
    throw new Error("Invalid url");
  }
  // If content or title is empty, pass only the URL to avoid a 422 error.
  const mustSaveContent = !!title && !!content;
  const data = mustSaveContent
    ? {
        url,
        title,
        content,
        content_type: contentType,
        language,
        must_extract_content: mustExtractContent,
      }
    : { url };
  try {
    return await post("/api/reading/articles/", data);
  } catch (error) {
    if (error instanceof Error && error.message === "Response status: 400 (Bad Request)") {
      // Content might be too big (we don't have a clean way to catch this yet), let's try to save only the URL.
      return await post("/api/reading/articles/", { url });
    }
    throw error;
  }
};

/**
 * @param {number} articleId
 * @param {UpdateArticlePayload} params
 * @returns {Promise<Article>}
 */
export const updateArticle = async (
  articleId,
  { title, tags, readAt, isFavorite, isForLater, readingTime },
) =>
  await patch(`/api/reading/articles/${articleId}/`, {
    title,
    tags,
    reading_time: readingTime,
    read_at: readAt,
    is_favorite: isFavorite,
    is_for_later: isForLater,
  });

/**
 * @param {number} articleId
 * @returns {Promise<{}>}
 */
export const deleteArticle = async (articleId) =>
  await httpDelete(`/api/reading/articles/${articleId}/`);

/**
 * @param {{articleUrls?: string[]}} params
 * @returns {Promise<{count: number, items: Article[]}>}
 */
export const listArticles = async ({ articleUrls }) => {
  const isFilteringByUrls = articleUrls && articleUrls.length > 0;
  if (!isFilteringByUrls) {
    return await get("/api/reading/articles/");
  }
  const queries = articleUrls
    .map(
      (articleUrl) => `/api/reading/articles/?q=${encodeURIComponent(articleUrl)}&search_type=url`,
    )
    .map((query) => get(query));
  const results = await Promise.all(queries);
  return results.reduce(
    (acc, result) => ({
      count: acc.count + result.items.length,
      items: [...acc.items, ...result.items],
    }),
    {
      count: 0,
      items: /** @type {Article[]} */ ([]),
    },
  );
};

/**
 * @param {string} link
 * @returns {Promise<Feed>}
 */
export const subscribeToFeed = async (link) => await post("/api/feeds/", { feed_url: link });

/**
 * @param {{feedUrls?: string[]}} params
 * @returns {Promise<{items: Feed[]}>}
 */
export const listEnabledFeeds = async ({ feedUrls }) => {
  let qs = "";
  const isFilteringByUrls = feedUrls && feedUrls.length > 0;
  if (isFilteringByUrls) {
    qs = feedUrls.map((feedUrl) => `feed_urls=${encodeURIComponent(feedUrl)}`).join("&");
    qs = `?${qs}&enabled=true`;
  }
  return await get(`/api/feeds/${qs}`);
};

/**
 * @param {number} feedId
 * @returns {Promise<{}>}
 */
export const deleteFeed = async (feedId) => await httpDelete(`/api/feeds/${feedId}/`);

/**
 * @param {number} feedId
 * @param {UpdateFeedPayload} params
 * @returns {Promise<Feed>}
 */
export const updateFeed = async (
  feedId,
  { categoryId, tags, refreshDelay, articleRetentionTime, disabledAt, disabledReason },
) =>
  await patch(`/api/feeds/${feedId}/`, {
    category_id: categoryId,
    tags,
    refresh_delay: refreshDelay,
    article_retention_time: articleRetentionTime,
    disabled_at: disabledAt,
    disabled_reason: disabledReason,
  });

/**
 * @returns {Promise<Tag[]>}
 */
export const listTags = async () => {
  const response = await get("/api/reading/tags/");
  return response.items;
};

/**
 * @returns {Promise<Category[]>}
 */
export const listCategories = async () => {
  const response = await get("/api/feeds/categories/");
  return response.items;
};

/**
 * @returns {Promise<void>}
 */
const ensureIsAuthenticated = async () => {
  const options = await loadOptions();
  if (mustJwtBeRenewed(options.accessToken)) {
    await getNewAccessToken(options);
  }
};

/**
 * @param {Options} options
 * @returns {Promise<void>}
 */
const getNewAccessToken = async (options) => {
  const data = await doFetch("/api/users/tokens/", {
    method: "POST",
    body: JSON.stringify({
      email: options.userEmail,
      application_token_uuid: options.tokenId,
      application_token_secret: options.tokenSecret,
    }),
  });
  await chrome.storage.local.set({ accessToken: data.access_token });
};

/**
 * @param {string} apiUrl
 * @param {any} data
 * @returns {Promise<any>}
 */
const post = async (apiUrl, data) =>
  await doFetch(/** @type {string} */ (apiUrl), {
    method: "POST",
    body: JSON.stringify(data),
  });

/**
 * @param {string} url
 * @param {RequestInit} fetchOptions
 * @returns {Promise<any>}
 */
const doFetch = async (url, fetchOptions) => {
  await ensureIsAuthenticated();
  const options = await loadOptions();
  if (!fetchOptions.headers) {
    fetchOptions.headers = {};
  }
  fetchOptions.headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${options.accessToken}`,
    .../** @type {Record<string, string>} */ (fetchOptions.headers),
  };
  const resp = await fetch(mergeUrlFragments(options.instanceUrl, url), fetchOptions);
  if (!resp.ok) {
    let detail = "";
    try {
      const body = await resp.json();
      detail = body.detail ?? body.message ?? JSON.stringify(body);
    } catch {
      // Response body is not JSON; ignore.
    }
    const message = detail
      ? `Response status: ${resp.status} (${resp.statusText}) — ${detail}`
      : `Response status: ${resp.status} (${resp.statusText})`;
    throw new Error(message, { cause: resp.status });
  }
  if (fetchOptions.method === "DELETE") {
    return {};
  }
  return await resp.json();
};

/**
 * @param {string} apiUrl
 * @param {any} data
 * @returns {Promise<any>}
 */
const patch = async (apiUrl, data) =>
  await doFetch(/** @type {string} */ (apiUrl), {
    method: "PATCH",
    body: JSON.stringify(data),
  });

/**
 * @param {string} apiUrl
 * @returns {Promise<any>}
 */
const get = async (apiUrl) => await doFetch(/** @type {string} */ (apiUrl), { method: "GET" });

/**
 * @param {string} apiUrl
 * @returns {Promise<{any}>}
 */
const httpDelete = async (apiUrl) =>
  await doFetch(/** @type {string} */ (apiUrl), { method: "DELETE" });

/**
 * @returns {Promise<Options>}
 */
export const loadOptions = async () => chrome.storage.local.get(DEFAULT_OPTIONS);

/**
 * @param {{instanceUrl: string, userEmail: string, tokenId: string, tokenSecret: string}} params
 * @returns {Promise<void>}
 */
export const storeOptions = async ({ instanceUrl, userEmail, tokenId, tokenSecret }) =>
  // Reset the access token when credentials options change.
  chrome.storage.local.set({ instanceUrl, userEmail, tokenId, tokenSecret, accessToken: "" });
