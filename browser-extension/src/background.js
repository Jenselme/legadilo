// SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
//
// SPDX-License-Identifier: AGPL-3.0-or-later

import {
  saveArticle,
  listTags,
  updateArticle,
  subscribeToFeed,
  updateFeed,
  listCategories,
  deleteArticle,
  deleteFeed,
} from "./legadilo.js";

const isFirefox = typeof browser === "object";

if (isFirefox) {
  browser.runtime.onConnect.addListener(function (port) {
    port.onMessage.addListener((request) => onMessage(request, port.postMessage));
  });
} else {
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    onMessage(request, sendResponse);

    return true;
  });
}

/**
 * @param request {MediaQueryList}
 */
const onMessage = async (request, sendResponse) => {
  try {
    switch (request.name) {
      case "save-article":
        await processSaveArticleRequest(sendResponse, request.payload);
        break;
      case "update-article":
        await processUpdateArticleRequest(sendResponse, request.articleId, request.payload);
        break;
      case "delete-article":
        await processDeleteArticleRequest(sendResponse, request.articleId);
        break;
      case "subscribe-to-feed":
        await processFeedSubscriptionRequest(sendResponse, request.payload);
        break;
      case "update-feed":
        await processUpdateFeedRequest(sendResponse, request.feedId, request.payload);
        break;
      case "delete-feed":
        await processDeleteFeedRequest(sendResponse, request.feedId);
        break;
      default:
        console.warn(`Unknown action ${request.name}`);
        break;
    }
  } catch (err) {
    sendResponse({ error: err.message });
  }
};

const processSaveArticleRequest = async (sendResponse, payload) => {
  const article = await saveArticle(payload);
  const tags = await listTags();
  sendResponse({ name: "saved-article", article, tags });
};

const processUpdateArticleRequest = async (sendResponse, articleId, payload) => {
  const article = await updateArticle(articleId, payload);
  const tags = await listTags();
  sendResponse({ name: "updated-article", article, tags });
};

const processDeleteArticleRequest = async (sendResponse, articleId) => {
  await deleteArticle(articleId);
  sendResponse({ name: "deleted-article" });
};

const processFeedSubscriptionRequest = async (sendResponse, payload) => {
  const feed = await subscribeToFeed(payload.link);
  const [tags, categories] = await Promise.all([listTags(), listCategories()]);
  sendResponse({ name: "subscribed-to-feed", feed, tags, categories });
};

const processUpdateFeedRequest = async (sendResponse, feedId, payload) => {
  const feed = await updateFeed(feedId, payload);
  const [tags, categories] = await Promise.all([listTags(), listCategories()]);
  sendResponse({ name: "updated-feed", feed, tags, categories });
};

const processDeleteFeedRequest = async (sendResponse, feedId) => {
  await deleteFeed(feedId);
  sendResponse({ name: "deleted-feed" });
};
