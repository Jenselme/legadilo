import {
  saveArticle,
  listTags,
  updateArticle,
  subscribeToFeed,
  updateFeed,
  listCategories,
} from "./legadilo.js";

let extPort;
browser.runtime.onConnect.addListener(function (port) {
  extPort = port;
  port.onMessage.addListener(onMessage);
});

/**
 * @param request {MediaQueryList}
 */
const onMessage = async (request) => {
  try {
    switch (request.name) {
      case "save-article":
        await processSaveArticleRequest(request.payload);
        break;
      case "update-article":
        await processUpdateArticleRequest(request.articleId, request.payload);
        break;
      case "subscribe-to-feed":
        await processFeedSubscriptionRequest(request.payload);
        break;
      case "update-feed":
        await processUpdateFeedRequest(request.feedId, request.payload);
        break;
      default:
        console.warn(`Unknown action ${request.name}`);
        break;
    }
  } catch (err) {
    extPort.postMessage({ error: err.message });
  }
};

const processSaveArticleRequest = async (payload) => {
  const article = await saveArticle(payload);
  const tags = await listTags();
  extPort.postMessage({ name: "saved-article", article, tags });
};

const processUpdateArticleRequest = async (articleId, payload) => {
  const article = await updateArticle(articleId, payload);
  const tags = await listTags();
  extPort.postMessage({ name: "updated-article", article, tags });
};

const processFeedSubscriptionRequest = async (payload) => {
  const feed = await subscribeToFeed(payload.link);
  const [tags, categories] = await Promise.all([listTags(), listCategories()]);
  extPort.postMessage({ name: "subscribed-to-feed", feed, tags, categories });
};

const processUpdateFeedRequest = async (feedId, payload) => {
  const feed = await updateFeed(feedId, payload);
  const [tags, categories] = await Promise.all([listTags(), listCategories()]);
  extPort.postMessage({ name: "updated-feed", feed, tags, categories });
};
