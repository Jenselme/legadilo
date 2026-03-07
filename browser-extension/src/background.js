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
  ensureIsAuthenticated,
  listCategories,
  listTags,
  saveArticle,
  subscribeToFeed,
  updateArticle,
  updateFeed,
} from "./legadilo.js";

/**
 * @typedef {Object} RequestMessage
 * @property {string} name
 * @property {number} [articleId]
 * @property {number} [feedId]
 * @property {SaveArticlePayload} [payload]
 */

const isFirefox = typeof browser === "object";

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
 * @param {RequestMessage} request
 * @param {(response: object) => void} sendResponse
 * @returns {Promise<void>}
 */
const onMessage = async (request, sendResponse) => {
  await ensureIsAuthenticated();

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
    sendResponse({ error: err instanceof Error ? err.message : String(err) });
  }
};

/**
 * @param {(response: object) => void} sendResponse
 * @param {SaveArticlePayload} payload
 * @returns {Promise<void>}
 */
const processSaveArticleRequest = async (sendResponse, payload) => {
  const article = await saveArticle(payload);
  const tags = await listTags();
  sendResponse({ name: "saved-article", article, tags });
};

/**
 * @param {(response: object) => void} sendResponse
 * @param {number} articleId
 * @param {UpdateArticlePayload} payload
 * @returns {Promise<void>}
 */
const processUpdateArticleRequest = async (sendResponse, articleId, payload) => {
  const article = await updateArticle(articleId, payload);
  const tags = await listTags();
  sendResponse({ name: "updated-article", article, tags });
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
  const [tags, categories] = await Promise.all([listTags(), listCategories()]);
  sendResponse({ name: "subscribed-to-feed", feed, tags, categories });
};

/**
 * @param {(response: object) => void} sendResponse
 * @param {number} feedId
 * @param {UpdateFeedPayload} payload
 * @returns {Promise<void>}
 */
const processUpdateFeedRequest = async (sendResponse, feedId, payload) => {
  const feed = await updateFeed(feedId, payload);
  const [tags, categories] = await Promise.all([listTags(), listCategories()]);
  sendResponse({ name: "updated-feed", feed, tags, categories });
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
