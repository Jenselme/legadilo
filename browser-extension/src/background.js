// SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
//
// SPDX-License-Identifier: AGPL-3.0-or-later

/** @typedef {import('./types.js').Article} Article */
/** @typedef {import('./types.js').Feed} Feed */
/** @typedef {import('./types.js').Tag} Tag */
/** @typedef {import('./types.js').Category} Category */
/** @typedef {import('./types.js').SaveArticlePayload} SaveArticlePayload */
/** @typedef {import('./types.js').UpdateArticlePayload} UpdateArticlePayload */
/** @typedef {import('./types.js').UpdateFeedPayload} UpdateFeedPayload */

import {
  deleteArticle,
  deleteFeed,
  loadOptions,
  saveArticle,
  subscribeToFeed,
  updateArticle,
  updateFeed,
} from "./legadilo.js";
import { getErrorMessage } from "./utils.js";

/**
 * @typedef {Object} RequestMessage
 * @property {string} name
 * @property {number} [articleId]
 * @property {number} [feedId]
 * @property {SaveArticlePayload} [payload]
 */

const isFirefox = typeof browser === "object";

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "save-link-as-article",
    title: "Save link as article in Legadilo",
    contexts: ["link"],
  });
});

/**
 * @param {number} tabId
 * @returns {Promise<void>}
 */
const updateExtensionForTab = async (tabId) => {
  const { url } = await chrome.tabs.get(tabId);
  if (!url) return;

  const { instanceUrl } = await loadOptions();
  const isInstanceUrl = url.startsWith(instanceUrl);
  const isBrowserInternalUrl = checkIsBrowserInternalUrl(url);
  const mustDisable = isInstanceUrl || isBrowserInternalUrl;
  if (mustDisable) {
    await chrome.action.disable(tabId);
  } else {
    await chrome.action.enable(tabId);
  }
  await chrome.contextMenus.update("save-link-as-article", { visible: !mustDisable });
};

chrome.tabs.onActivated.addListener(async ({ tabId }) => {
  await updateExtensionForTab(tabId);
});

chrome.tabs.onUpdated.addListener(async (tabId, changeInfo) => {
  if (changeInfo.status === "complete") {
    await updateExtensionForTab(tabId);
  }
});

chrome.contextMenus.onClicked.addListener(async (info) => {
  if (info.menuItemId !== "save-link-as-article" || !info.linkUrl) {
    return;
  }

  try {
    await saveArticle({
      url: info.linkUrl,
      title: "",
      content: "",
      contentType: "text/html",
      language: "",
      mustExtractContent: true,
    });
  } catch (err) {
    console.error("Failed to save article from context menu:", err);
  }
});

if (isFirefox) {
  browser.runtime.onConnect.addListener(function (port) {
    port.onMessage.addListener((/** @type {RequestMessage} */ request) =>
      onMessage(request, port.postMessage.bind(port)),
    );
  });
} else {
  chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
    onMessage(request, sendResponse);

    return true;
  });
}

/**
 * @param {string} url
 * @returns {boolean}
 */
const checkIsBrowserInternalUrl = (url) =>
  url.startsWith("chrome://") ||
  url.startsWith("moz-extension://") ||
  (url.startsWith("about:") && !url.startsWith("about:reader?"));

export const __test__ = { checkIsBrowserInternalUrl };

/**
 * @param {RequestMessage} request
 * @param {(response: object) => void} sendResponse
 * @returns {Promise<void>}
 */
const onMessage = async (request, sendResponse) => {
  try {
    switch (request.name) {
      case "save-article":
        await processSaveArticleRequest(
          sendResponse,
          /** @type {SaveArticlePayload} */ (request.payload),
        );
        break;
      case "update-article":
        await processUpdateArticleRequest(
          sendResponse,
          /** @type {number} */ (request.articleId),
          /** @type {UpdateArticlePayload} */ (/** @type {unknown} */ (request.payload)),
        );
        break;
      case "delete-article":
        await processDeleteArticleRequest(sendResponse, /** @type {number} */ (request.articleId));
        break;
      case "subscribe-to-feed":
        await processFeedSubscriptionRequest(
          sendResponse,
          /** @type {{link: string}} */ (/** @type {unknown} */ (request.payload)),
        );
        break;
      case "update-feed":
        await processUpdateFeedRequest(
          sendResponse,
          /** @type {number} */ (request.feedId),
          /** @type {UpdateFeedPayload} */ (/** @type {unknown} */ (request.payload)),
        );
        break;
      case "delete-feed":
        await processDeleteFeedRequest(sendResponse, /** @type {number} */ (request.feedId));
        break;
      default:
        console.warn(`Unknown action ${request.name}`);
        break;
    }
  } catch (err) {
    sendResponse({ error: getErrorMessage(err) });
  }
};

/**
 * @param {(response: object) => void} sendResponse
 * @param {SaveArticlePayload} payload
 * @returns {Promise<void>}
 */
const processSaveArticleRequest = async (sendResponse, payload) => {
  const article = await saveArticle(payload);
  sendResponse({ name: "saved-article", article });
};

/**
 * @param {(response: object) => void} sendResponse
 * @param {number} articleId
 * @param {UpdateArticlePayload} payload
 * @returns {Promise<void>}
 */
const processUpdateArticleRequest = async (sendResponse, articleId, payload) => {
  const article = await updateArticle(articleId, payload);
  sendResponse({ name: "updated-article", article });
};

/**
 * @param {(response: object) => void} sendResponse
 * @param {number} articleId
 * @returns {Promise<void>}
 */
const processDeleteArticleRequest = async (sendResponse, articleId) => {
  await deleteArticle(articleId);
  sendResponse({ name: "deleted-article" });
};

/**
 * @param {(response: object) => void} sendResponse
 * @param {{link: string}} payload
 * @returns {Promise<void>}
 */
const processFeedSubscriptionRequest = async (sendResponse, payload) => {
  const feed = await subscribeToFeed(payload.link);
  sendResponse({ name: "subscribed-to-feed", feed });
};

/**
 * @param {(response: object) => void} sendResponse
 * @param {number} feedId
 * @param {UpdateFeedPayload} payload
 * @returns {Promise<void>}
 */
const processUpdateFeedRequest = async (sendResponse, feedId, payload) => {
  const feed = await updateFeed(feedId, payload);
  sendResponse({ name: "updated-feed", feed });
};

/**
 * @param {(response: object) => void} sendResponse
 * @param {number} feedId
 * @returns {Promise<void>}
 */
const processDeleteFeedRequest = async (sendResponse, feedId) => {
  await deleteFeed(feedId);
  sendResponse({ name: "deleted-feed" });
};
