const DEFAULT_LEGADILO_URL = "https://www.legadilo.eu";

export const DEFAULT_OPTIONS = {
  instanceUrl: DEFAULT_LEGADILO_URL,
  applicationToken: "",
};

export const saveArticle = async ({ link, title, content } = {}) => {
  if (!/^https?:\/\//.test(link)) {
    throw new Error("Invalid url");
  }

  return await post({ link, title, content });
};

const post = async (data) => {
  const options = await loadOptions();

  const resp = await fetch(`${options.instanceUrl}/api/reading/articles/`, {
    method: "POST",
    headers: buildHeaders(options),
    body: JSON.stringify(data),
  });

  if (!resp.ok) {
    throw new Error(`Response status: ${resp.status} (${resp.statusText})`);
  }

  return await resp.json();
};

const buildHeaders = (options) => ({
  "Content-Type": "application/json",
  Authorization: `Bearer ${options.applicationToken}`,
});

export const loadOptions = async () => chrome.storage.local.get(DEFAULT_OPTIONS);

export const storeOptions = async ({ instanceUrl, applicationToken }) =>
  chrome.storage.local.set({ instanceUrl, applicationToken });
