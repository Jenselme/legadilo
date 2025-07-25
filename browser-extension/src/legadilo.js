// SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
//
// SPDX-License-Identifier: AGPL-3.0-or-later

const DEFAULT_LEGADILO_URL = "https://www.legadilo.eu";

export const DEFAULT_OPTIONS = {
  instanceUrl: DEFAULT_LEGADILO_URL,
  userEmail: "",
  tokenId: "",
  tokenSecret: "",
  accessToken: "",
};

export const testCredentials = async ({ instanceUrl, userEmail, tokenId, tokenSecret }) => {
  try {
    const resp = await fetch(`${instanceUrl}/api/users/tokens/`, {
      "Content-Type": "application/json",
      method: "POST",
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

export const saveArticle = async ({ url, title, content }) => {
  if (!/^https?:\/\//.test(url)) {
    throw new Error("Invalid url");
  }

  // If content or title is empty, pass only the URL to avoid a 422 error.
  const data = !!title && !!content ? { url, title, content } : { url };

  try {
    return await post("/api/reading/articles/", data);
  } catch (error) {
    if (error.message === "Response status: 400 (Bad Request)") {
      // Content might be too big (we don't have a clean way to catch this yet), let's try to save only the URL.
      return await post("/api/reading/articles/", { url });
    }

    throw error;
  }
};

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

export const deleteArticle = async (articleId) =>
  await httpDelete(`/api/reading/articles/${articleId}/`);

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
      items: [],
    },
  );
};

export const subscribeToFeed = async (link) => await post("/api/feeds/", { feed_url: link });

export const listEnabledFeeds = async ({ feedUrls }) => {
  let qs = "";
  const isFilteringByUrls = feedUrls && feedUrls.length > 0;
  if (isFilteringByUrls) {
    qs = feedUrls.map((feedUrl) => `feed_urls=${encodeURIComponent(feedUrl)}`).join("&");
    qs = `?${qs}&enabled=true`;
  }

  return await get(`/api/feeds/${qs}`);
};

export const deleteFeed = async (feedId) => await httpDelete(`/api/feeds/${feedId}/`);

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

export const listTags = async () => {
  const response = await get("/api/reading/tags/");

  return response.items;
};

export const listCategories = async () => {
  const response = await get("/api/feeds/categories/");

  return response.items;
};

const handleAuth =
  (fetchFunc) =>
  async (...fetchArgs) => {
    const options = await loadOptions();
    // If we don’t have a token yet, we create one.
    if (!options.accessToken) {
      await getNewAccessToken(options);
    }

    try {
      return await fetchFunc(...fetchArgs);
    } catch (error) {
      // Error is unrelated to auth, let’s propagate immediately.
      if (![401, 403].includes(error.cause)) {
        throw error;
      }
    }

    // The current token has probably expired. Let’s get a new one and retry. If it fails again,
    // let the error propagate.
    await getNewAccessToken(options);
    return await fetchFunc(...fetchArgs);
  };

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

  return data.access_token;
};

const post = handleAuth(
  async (apiUrl, data) => await doFetch(apiUrl, { method: "POST", body: JSON.stringify(data) }),
);

const doFetch = async (url, fetchOptions) => {
  const options = await loadOptions();

  if (!fetchOptions.headers) {
    fetchOptions.headers = {};
  }

  fetchOptions.headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${options.accessToken}`,
    ...fetchOptions.headers,
  };

  const resp = await fetch(`${options.instanceUrl}${url}`, fetchOptions);

  if (!resp.ok) {
    throw new Error(`Response status: ${resp.status} (${resp.statusText})`, {
      cause: resp.status,
    });
  }

  if (fetchOptions.method === "DELETE") {
    return {};
  }

  return await resp.json();
};

const patch = handleAuth(
  async (apiUrl, data) => await doFetch(apiUrl, { method: "PATCH", body: JSON.stringify(data) }),
);

const get = handleAuth(async (apiUrl) => await doFetch(apiUrl, { method: "GET" }));

const httpDelete = handleAuth(async (apiUrl) => await doFetch(apiUrl, { method: "DELETE" }));

export const loadOptions = async () => chrome.storage.local.get(DEFAULT_OPTIONS);

export const storeOptions = async ({ instanceUrl, userEmail, tokenId, tokenSecret }) =>
  // Reset access token when options change.
  chrome.storage.local.set({ instanceUrl, userEmail, tokenId, tokenSecret, accessToken: "" });
