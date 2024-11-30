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
 * @param msg {MediaQueryList}
 */
const onMessage = async (msg) => {
  try {
    switch (msg.request) {
      case "save-article":
        await processSaveArticleRequest(msg.payload);
        break;
      case "update-article":
        await processUpdateArticleRequest(msg.articleId, msg.payload);
        break;
      case "subscribe-to-feed":
        await processFeedSubscriptionRequest(msg.payload);
        break;
      case "update-feed":
        await processUpdateFeedRequest(msg.feedId, msg.payload);
        break;
      default:
        console.warn(`Unknown action ${msg.request}`);
        break;
    }
  } catch (err) {
    extPort.postMessage({ error: err.message });
  }
};

const processSaveArticleRequest = async (payload) => {
  const article = await saveArticle(payload);
  const tags = await listTags();
  extPort.postMessage({ request: "saved-article", article, tags });
};

const processUpdateArticleRequest = async (articleId, payload) => {
  const article = await updateArticle(articleId, payload);
  const tags = await listTags();
  extPort.postMessage({ request: "updated-article", article, tags });
};

const processFeedSubscriptionRequest = async (payload) => {
  const feed = await subscribeToFeed(payload.link);
  const [tags, categories] = await Promise.all([listTags(), listCategories()]);
  extPort.postMessage({ request: "subscribed-to-feed", feed, tags, categories });
};

const processUpdateFeedRequest = async (feedId, payload) => {
  const feed = await updateFeed(feedId, payload);
  const [tags, categories] = await Promise.all([listTags(), listCategories()]);
  extPort.postMessage({ request: "updated-feed", feed, tags, categories });
};
