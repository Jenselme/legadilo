const DEFAULT_LEGADILO_URL = "https://www.legadilo.eu";

export const DEFAULT_OPTIONS = {
  instanceUrl: DEFAULT_LEGADILO_URL,
  userEmail: "",
  tokenId: "",
  tokenSecret: "",
  accessToken: "",
};

export const saveArticle = async ({ link, title, content }) => {
  if (!/^https?:\/\//.test(link)) {
    throw new Error("Invalid url");
  }

  return await post("/api/reading/articles/", { link, title, content });
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

export const subscribeToFeed = async (link) => await post("/api/feeds/", { feed_url: link });

export const updateFeed = async (
  feedId,
  { categoryId, tags, refreshDelay, articleRetentionTime },
) =>
  await patch(`/api/feeds/${feedId}/`, {
    category_id: categoryId,
    tags,
    refresh_delay: refreshDelay,
    article_retention_time: articleRetentionTime,
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
    throw new Error(`Response status: ${resp.status} (${resp.statusText})`, { cause: resp.status });
  }

  return await resp.json();
};

const patch = handleAuth(
  async (apiUrl, data) => await doFetch(apiUrl, { method: "PATCH", body: JSON.stringify(data) }),
);

const get = handleAuth(async (apiUrl) => await doFetch(apiUrl, { method: "GET" }));

export const loadOptions = async () => chrome.storage.local.get(DEFAULT_OPTIONS);

export const storeOptions = async ({ instanceUrl, userEmail, tokenId, tokenSecret }) =>
  // Reset access token when options change.
  chrome.storage.local.set({ instanceUrl, userEmail, tokenId, tokenSecret, accessToken: "" });
