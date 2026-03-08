// SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
//
// SPDX-License-Identifier: AGPL-3.0-or-later

/** @typedef {import('./types.js').Tag} Tag */
/** @typedef {import('./types.js').Category} Category */
/** @typedef {import('./types.js').Article} Article */
/** @typedef {import('./types.js').Feed} Feed */
/** @typedef {import('./types.js').UpdateArticlePayload} UpdateArticlePayload */
/** @typedef {import('./types.js').UpdateFeedPayload} UpdateFeedPayload */

import Tags from "./vendor/tags.js";
import { listArticles, listEnabledFeeds } from "./legadilo.js";
import {
  getDialogById,
  getElementById,
  getFormById,
  getInputElementById,
  getLinkElementById,
  getSelectElementById,
} from "./typing-utils.js";
import Readability from "./vendor/Readability.js";

/**
 * @typedef {Object} ArticleData
 * @property {string} content
 * @property {string} pageContent
 * @property {string} contentType
 * @property {string} title
 * @property {string} language
 * @property {boolean} mustExtractContent
 */

/**
 * @typedef {Object} ResponseMessage
 * @property {string} [error]
 * @property {string} [name]
 * @property {Article} [article]
 * @property {Feed} [feed]
 * @property {Tag[]} [tags]
 * @property {Category[]} [categories]
 */

/**
 * @typedef {Object} OutboundMessage
 * @property {string} name
 * @property {number} [articleId]
 * @property {number} [feedId]
 * @property {object} [payload]
 */

/** @type {chrome.runtime.Port | undefined} */
let port;
/** @type {ReturnType<typeof Tags.init> | null} */
let articleTagsInstance = null;
/** @type {ReturnType<typeof Tags.init> | null} */
let feedTagsInstance = null;

const isFirefox = typeof browser === "object";

document.addEventListener("DOMContentLoaded", () => {
  connectToPort();

  hideLoader();
  hideErrorMessage();
  hideActionSelector();
  hideArticle();
  hideFeed();

  runDefaultAction();
});

/**
 * @returns {void}
 */
const connectToPort = () => {
  if (!isFirefox) {
    return;
  }

  port = chrome.runtime.connect({ name: "legadilo-popup" });
  port.onMessage.addListener(onMessage);
};

/**
 * @returns {Promise<void>}
 */
const runDefaultAction = async () => {
  const tab = await getCurrentTab();
  const data = await getPageContent(tab);
  const feedNodes = getFeedNodes(data.pageContent, data.contentType);

  // No feed links, let's save immediately.
  if (feedNodes.length === 0) {
    await saveArticle(tab, data);
    return;
  }

  await displayActionsSelector();
};

/**
 * @param {string} pageContent
 * @param {string} contentType
 * @returns {Element[]}
 */
const getFeedNodes = (pageContent, contentType) => {
  if (contentType === "text/plain") return [];

  const parser = new DOMParser();
  const htmlDoc = parser.parseFromString(
    pageContent,
    /** @type {DOMParserSupportedType} */ (contentType),
  );
  const feedNodes = /** @type {Element[]} */ ([]);
  feedNodes.push(...htmlDoc.querySelectorAll('[type="application/rss+xml"]'));
  feedNodes.push(...htmlDoc.querySelectorAll('[type="application/atom+xml"]'));

  return feedNodes;
};

/**
 * @param {chrome.tabs.Tab} tab
 * @param {ArticleData} data
 * @returns {string | null}
 */
const getCanonicalUrl = (tab, data) => {
  if (data.contentType === "text/plain") return null;

  const parser = new DOMParser();
  const htmlDoc = parser.parseFromString(
    data.pageContent,
    /** @type {DOMParserSupportedType} */ (data.contentType),
  );

  const canonicalLink = htmlDoc.querySelector("link[rel='canonical']");
  if (!canonicalLink) {
    return null;
  }

  return buildFullUrl(tab, canonicalLink.getAttribute("href") ?? "");
};

/**
 * @param {ResponseMessage} request
 * @returns {void}
 */
const onMessage = (request) => {
  if (request.error) {
    hideLoader();
    displayErrorMessage(request.error);
    return;
  }

  hideErrorMessage();
  hideLoader();
  switch (request.name) {
    case "saved-article":
      savedArticleSuccess(
        /** @type {Article} */ (request.article),
        /** @type {Tag[]} */ (request.tags),
      );
      break;
    case "updated-article":
      updatedArticleSuccess(
        /** @type {Article} */ (request.article),
        /** @type {Tag[]} */ (request.tags),
      );
      break;
    case "deleted-article":
      displayActionsSelector();
      break;
    case "subscribed-to-feed":
      feedSubscriptionSuccess(
        /** @type {Feed} */ (request.feed),
        /** @type {Tag[]} */ (request.tags),
        /** @type {Category[]} */ (request.categories),
      );
      break;
    case "updated-feed":
      updatedFeedSuccess(
        /** @type {Feed} */ (request.feed),
        /** @type {Tag[]} */ (request.tags),
        /** @type {Category[]} */ (request.categories),
      );
      break;
    case "deleted-feed":
      displayActionsSelector();
      break;
    default:
      console.warn(`Unknown action ${request.name}`);
  }
};

/**
 * @returns {Promise<void>}
 */
const displayActionsSelector = async () => {
  displayLoader();
  const tab = await getCurrentTab();
  const data = await getPageContent(tab);
  const feedNodes = getFeedNodes(data.pageContent, data.contentType);
  const feedUrls = feedNodes.map((feedNode) => getFeedHref(tab, feedNode));
  const pageUrl = getPageUrlFromTab(tab);
  const articleUrls = [pageUrl];
  const articleCanonicalUrl = getCanonicalUrl(tab, data);
  if (articleCanonicalUrl) {
    articleUrls.push(articleCanonicalUrl);
  }
  let savedArticles = /** @type {Article[]} */ ([]);
  try {
    savedArticles = (await listArticles({ articleUrls })).items;
  } catch {
    console.error("Failed to list saved articles.");
  }
  let subscribedFeedUrls = /** @type {string[]} */ ([]);
  try {
    subscribedFeedUrls = (await listEnabledFeeds({ feedUrls })).items.map((feed) => feed.feed_url);
  } catch {
    console.error("Failed to list enabled feeds.");
  }
  hideLoader();

  getElementById("article-already-saved").hidden = savedArticles.length === 0;

  getElementById("action-selector-container").hidden = false;

  const chooseFeedsContainer = getElementById("subscribe-to-feeds-container");
  chooseFeedsContainer.replaceChildren();

  for (const feedNode of feedNodes) {
    let feedHref = getFeedHref(tab, feedNode);

    const button = document.createElement("button");
    button.classList.add("btn", "btn-outline-primary", "mb-2", "col");
    let feedTitle = feedNode.getAttribute("title");
    if (!feedTitle) {
      const hostname = new URL(pageUrl).hostname;
      const type = feedNode.getAttribute("type") ?? "";
      const feedType = type.replace("application/", "").replace("+xml", "");
      feedTitle = `${hostname} (${feedType})`;
    }

    button.innerHTML = `${feedTitle} ${
      subscribedFeedUrls.includes(feedHref)
        ? '<svg class="bi" role="img" aria-label="Already subscribed to this feed"><use href="./bs-sprite.svg#rss-fill"></use></svg>'
        : ""
    }`;

    button.addEventListener("click", () => {
      hideActionSelector();
      subscribeToFeed(feedHref);
    });
    chooseFeedsContainer.appendChild(button);
  }

  getElementById("save-article-action-btn").addEventListener("click", async () => {
    hideActionSelector();
    await saveArticle(tab, data);
  });
};

/**
 * @param {chrome.tabs.Tab} tab
 * @param {Element} feedNode
 * @returns {string}
 */
const getFeedHref = (tab, feedNode) => {
  const feedHref = feedNode.getAttribute("href") ?? "";
  return buildFullUrl(tab, feedHref);
};

/**
 * @param {chrome.tabs.Tab} tab
 * @param {string} url
 * @returns {string}
 */
const buildFullUrl = (tab, url) => {
  if (/^https?:\/\//.test(url)) {
    return url;
  }

  const pageUrl = getPageUrlFromTab(tab);
  if (url.startsWith("//")) {
    const pageProtocol = new URL(pageUrl).protocol;
    return `${pageProtocol}${url}`;
  }

  const origin = new URL(pageUrl).origin;
  return `${origin}${url}`;
};

/**
 * @returns {void}
 */
const hideActionSelector = () => {
  getElementById("action-selector-container").hidden = true;
};

/**
 * @returns {Promise<void>}
 */
const errorNavBack = async () => {
  hideErrorMessage();
  await displayActionsSelector();
  getElementById("error-nav-back").removeEventListener("click", errorNavBack);
};

/**
 * @param {string} message
 * @returns {void}
 */
const displayErrorMessage = (message) => {
  getElementById("error-message").innerText = message;
  getElementById("error-container").hidden = false;

  getElementById("error-nav-back").addEventListener("click", errorNavBack);
};

/**
 * @returns {void}
 */
const hideErrorMessage = () => {
  getElementById("error-container").hidden = true;
};

/**
 * @returns {void}
 */
const displayLoader = () => {
  getElementById("loading-indicator-container").hidden = false;
};

/**
 * @returns {void}
 */
const hideLoader = () => {
  getElementById("loading-indicator-container").hidden = true;
};

/**
 * @param {string} element
 * @param {Tag[]} tags
 * @param {Tag[]} selectedTags
 * @returns {ReturnType<typeof Tags.init>}
 */
const createTagInstance = (element, tags, selectedTags) => {
  /** @type {Record<string, Tag[]>} */
  const tagsHierarchy = tags.reduce((acc, tag) => ({ ...acc, [tag.slug]: tag.sub_tags }), {});

  return Tags.init(element, {
    allowNew: true,
    allowClear: true,
    items: tags.reduce(
      (/** @type {Record<string, string>} */ acc, tag) => ({ ...acc, [tag.slug]: tag.title }),
      {},
    ),
    selected: selectedTags.map((tag) => tag.slug),
    onSelectItem(item, instance) {
      if (!Array.isArray(tagsHierarchy[item.value])) {
        return;
      }

      const alreadyAddedItems = instance.getSelectedValues();
      tagsHierarchy[item.value]
        .filter((tag) => !alreadyAddedItems.includes(tag.slug))
        .forEach((tag) => instance.addItem(tag.title, tag.slug));
    },
  });
};

/**
 * @param {Article} article
 * @param {Tag[]} tags
 * @returns {void}
 */
const displayArticle = (article, tags) => {
  getElementById("article-container").hidden = false;

  getInputElementById("saved-article-title").value = article.title;
  getInputElementById("saved-article-reading-time").value = String(article.reading_time);

  if (articleTagsInstance === null) {
    articleTagsInstance = createTagInstance("#saved-article-tags", tags, article.tags);
  }

  getElementById("mark-article-as-read").hidden = article.is_read;
  getElementById("mark-article-as-unread").hidden = !article.is_read;
  getElementById("mark-article-as-favorite").hidden = article.is_favorite;
  getElementById("unmark-article-as-favorite").hidden = !article.is_favorite;
  getElementById("mark-article-as-for-later").hidden = article.is_for_later;
  getElementById("unmark-article-as-for-later").hidden = !article.is_for_later;

  getLinkElementById("open-article-details").href = article.details_url;
};

/**
 * @returns {void}
 */
const hideArticle = () => {
  getElementById("article-container").hidden = true;
};

/**
 * @param {Feed} feed
 * @param {Tag[]} tags
 * @param {Category[]} categories
 * @returns {void}
 */
const displayFeed = (feed, tags, categories) => {
  getElementById("feed-container").hidden = false;
  getElementById("feed-title").innerText = feed.title;

  getInputElementById("feed-refresh-delay").value = String(feed.refresh_delay);
  getInputElementById("feed-article-retention-time").value = String(feed.article_retention_time);

  getLinkElementById("open-feed-details").href = feed.details_url;

  getElementById("enable-feed").hidden = feed.enabled;
  getElementById("disable-feed").hidden = !feed.enabled;

  const categorySelector = getSelectElementById("feed-category");
  // Clean all existing choices.
  categorySelector.innerHTML = "";
  const noCategoryOption = document.createElement("option");
  noCategoryOption.value = "";
  noCategoryOption.innerText = "No Category";
  categorySelector.appendChild(noCategoryOption);
  for (const category of categories) {
    const option = document.createElement("option");
    option.value = String(category.id);
    option.innerText = category.title;
    categorySelector.appendChild(option);
  }
  categorySelector.value = feed.category ? String(feed.category.id) : "";

  if (feedTagsInstance === null) {
    feedTagsInstance = createTagInstance("#feed-tags", tags, feed.tags);
  }
};

/**
 * @param {number} feedId
 * @returns {void}
 */
const setupFeedActions = (feedId) => {
  /**
   * @param {UpdateFeedPayload} payload
   * @returns {void}
   */
  const updateFeed = (payload) => {
    hideFeed();
    displayLoader();
    sendMessage({
      name: "update-feed",
      feedId: feedId,
      payload,
    });
  };

  const deleteFeed = () => {
    hideFeed();
    displayLoader();
    sendMessage({
      name: "delete-feed",
      feedId,
    });
  };

  /** @type {Record<string, (event: Event) => void>} */
  const actions = {
    "update-feed": (event) => {
      event.preventDefault();
      const data = new FormData(getFormById("update-feed-form"));
      updateFeed({
        categoryId: Number(data.get("category")) || null,
        refreshDelay: data.get("refresh-delay")?.toString() || "DAILY_AT_NOON",
        articleRetentionTime: Number(data.get("retention-time")),
        tags: /** @type {string[]} */ (data.getAll("tags")),
      });
    },
    "enable-feed": () => updateFeed({ disabledAt: null, disabledReason: null }),
    "disable-feed": () =>
      updateFeed({
        disabledAt: new Date().toISOString(),
        disabledReason: "Disable manually in the browser extension",
      }),
    "delete-feed": () =>
      askConfirmation("Are you sure you want to delete this feed?").then(deleteFeed),
    "feed-nav-back": async () => {
      Object.entries(actions).forEach(([selector, action]) => {
        getElementById(selector).removeEventListener("click", action);
      });

      hideFeed();
      await displayActionsSelector();
    },
  };

  Object.entries(actions).forEach(([selector, action]) => {
    getElementById(selector).addEventListener("click", action);
  });
};

/**
 * @returns {void}
 */
const hideFeed = () => {
  getElementById("feed-container").hidden = true;
};

/**
 * @returns {Promise<chrome.tabs.Tab>}
 */
const getCurrentTab = () =>
  chrome.tabs.query({ currentWindow: true, active: true }).then((tabs) => tabs[0]);

/**
 * @param {chrome.tabs.Tab} tab
 * @returns {Promise<ArticleData>}
 */
const getPageContent = async (tab) => {
  try {
    const getcontentTypeScriptResult = await chrome.scripting.executeScript({
      target: { tabId: /** @type {number} */ (tab.id) },
      func: () => document.contentType,
    });
    const contentType = getcontentTypeScriptResult[0].result ?? "text/plain";
    const getPageContentScriptResult = await chrome.scripting.executeScript({
      target: { tabId: /** @type {number} */ (tab.id) },
      func: () =>
        document.contentType === "text/plain"
          ? document.documentElement.outerText
          : document.documentElement.outerHTML,
    });
    const content = getPageContentScriptResult[0].result ?? "";

    let readabilityArticle = null;
    if (contentType !== "text/plain") {
      const parser = new DOMParser();
      const htmlDoc = parser.parseFromString(
        content,
        /** @type {DOMParserSupportedType} */ (contentType),
      );
      readabilityArticle = new Readability(htmlDoc, {}).parse();
    }

    return {
      title: readabilityArticle?.title || tab.title || "",
      contentType,
      content: readabilityArticle?.content || content,
      pageContent: content,
      language: readabilityArticle?.lang || "",
      mustExtractContent: !readabilityArticle?.content,
    };
  } catch (error) {
    console.error(error);
    return {
      title: tab.title || "",
      contentType: "text/plain",
      content: "",
      pageContent: "",
      language: "",
      mustExtractContent: false,
    };
  }
};

/**
 * @param {chrome.tabs.Tab} tab
 * @param {ArticleData} data
 * @returns {Promise<void>}
 */
const saveArticle = (tab, { title, content, contentType, language, mustExtractContent }) => {
  displayLoader();
  return sendMessage({
    name: "save-article",
    payload: {
      url: getPageUrlFromTab(tab),
      title,
      content,
      contentType,
      language: language,
      mustExtractContent,
    },
  });
};

/**
 * @param {chrome.tabs.Tab} tab
 * @returns {string}
 */
const getPageUrlFromTab = (tab) => {
  const url = tab.url ?? "";
  if (url.startsWith("about:")) {
    const internalUrlLike = url.replace("about:", "http://");
    const parsedInternalUrl = new URL(internalUrlLike);
    return parsedInternalUrl.searchParams.get("url") ?? "";
  }

  return url;
};

/**
 * @param {Article} article
 * @param {Tag[]} tags
 * @returns {void}
 */
const savedArticleSuccess = (article, tags) => {
  displayArticle(article, tags);
  setupArticleActions(article.id);
};

/**
 * @param {number} articleId
 * @returns {void}
 */
const setupArticleActions = (articleId) => {
  /**
   * @param {Partial<UpdateArticlePayload>} payload
   * @returns {void}
   */
  const updateArticle = (payload) => {
    hideArticle();
    displayLoader();
    sendMessage({
      name: "update-article",
      articleId,
      payload,
    });
  };

  const deleteArticle = () => {
    hideArticle();
    displayLoader();
    sendMessage({
      name: "delete-article",
      articleId,
    });
  };

  /** @type {Record<string, (event: Event) => void>} */
  const actions = {
    "update-saved-article": (event) => {
      event.preventDefault();

      const data = new FormData(getFormById("update-saved-article-form"));

      updateArticle({
        title: /** @type {string} */ (data.get("title")),
        tags: /** @type {string[]} */ (data.getAll("tags")),
        readingTime: Number(data.get("reading-time")),
      });
    },
    "mark-article-as-read": () => {
      updateArticle({ readAt: new Date().toISOString() });
    },
    "mark-article-as-unread": () => {
      updateArticle({ readAt: null });
    },
    "mark-article-as-favorite": () => {
      updateArticle({ isFavorite: true });
    },
    "unmark-article-as-favorite": () => {
      updateArticle({ isFavorite: false });
    },
    "mark-article-as-for-later": () => {
      updateArticle({ isForLater: true });
    },
    "unmark-article-as-for-later": () => {
      updateArticle({ isForLater: false });
    },
    "delete-article": () =>
      askConfirmation("Are you sure you want to delete this article?").then(deleteArticle),
    "article-nav-back": async () => {
      hideArticle();

      Object.entries(actions).forEach(([selector, action]) => {
        getElementById(selector).removeEventListener("click", action);
      });

      await displayActionsSelector();
    },
  };

  Object.entries(actions).forEach(([selector, action]) => {
    getElementById(selector).addEventListener("click", action);
  });
};

/**
 * @param {Article} article
 * @param {Tag[]} tags
 * @returns {void}
 */
const updatedArticleSuccess = (article, tags) => {
  displayArticle(article, tags);
};

/**
 * @param {string} link
 * @returns {void}
 */
const subscribeToFeed = (link) => {
  displayLoader();
  sendMessage({
    name: "subscribe-to-feed",
    payload: { link },
  });
};

/**
 * @param {Feed} feed
 * @param {Tag[]} tags
 * @param {Category[]} categories
 * @returns {void}
 */
const feedSubscriptionSuccess = (feed, tags, categories) => {
  displayFeed(feed, tags, categories);
  setupFeedActions(feed.id);
};

/**
 * @param {Feed} feed
 * @param {Tag[]} tags
 * @param {Category[]} categories
 * @returns {void}
 */
const updatedFeedSuccess = (feed, tags, categories) => {
  displayFeed(feed, tags, categories);
};

/**
 * @param {OutboundMessage} message
 * @returns {Promise<void>}
 */
const sendMessage = async (message) => {
  if (isFirefox) {
    /** @type {chrome.runtime.Port} */ (port).postMessage(message);
    return;
  }

  const response = await chrome.runtime.sendMessage(message);
  onMessage(response);
};

/**
 * @param {string} message
 * @returns {Promise<void>}
 */
const askConfirmation = (message) => {
  const confirmDialog = getDialogById("confirm-dialog");

  getElementById("confirm-dialog-title").innerText = message;

  /** @type {() => void} */
  let resolveDeferred;
  const deferred = new Promise((resolve) => {
    resolveDeferred = /** @type {() => void} */ (resolve);
  });
  const cancelBtn = getElementById("confirm-dialog-cancel-btn");
  const confirmBtn = getElementById("confirm-dialog-confirm-btn");
  const cancel = () => {
    confirmDialog.close();
    resolveDeferred();
    cancelBtn.removeEventListener("click", cancel);
    confirmBtn.removeEventListener("click", confirm);
  };
  const confirm = () => {
    confirmDialog.close();
    resolveDeferred();
    cancelBtn.removeEventListener("click", cancel);
    confirmBtn.removeEventListener("click", confirm);
  };

  cancelBtn.addEventListener("click", cancel);
  confirmBtn.addEventListener("click", confirm);

  confirmDialog.showModal();

  return deferred;
};
