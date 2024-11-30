const DEFAULT_LEGADILO_URL = "https://www.legadilo.eu";

export const DEFAULT_OPTIONS = {
  instanceUrl: DEFAULT_LEGADILO_URL,
  applicationToken: "",
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

export const listTags = async () => {
  const response = await get("/api/reading/tags/");

  return response.items;
};

const post = async (apiUrl, data) =>
  await doFetch(apiUrl, { method: "POST", body: JSON.stringify(data) });

const doFetch = async (url, fetchOptions) => {
  const options = await loadOptions();

  if (!fetchOptions.headers) {
    fetchOptions.headers = {};
  }

  fetchOptions.headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${options.applicationToken}`,
    ...fetchOptions.headers,
  };

  const resp = await fetch(`${options.instanceUrl}${url}`, fetchOptions);

  if (!resp.ok) {
    throw new Error(`Response status: ${resp.status} (${resp.statusText})`);
  }

  return await resp.json();
};

const patch = async (apiUrl, data) =>
  await doFetch(apiUrl, { method: "PATCH", body: JSON.stringify(data) });

const get = async (apiUrl) => await doFetch(apiUrl, { method: "GET" });

export const loadOptions = async () => chrome.storage.local.get(DEFAULT_OPTIONS);

export const storeOptions = async ({ instanceUrl, applicationToken }) =>
  chrome.storage.local.set({ instanceUrl, applicationToken });
