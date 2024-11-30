import { saveArticle, listTags, updateArticle } from "./legadilo.js";

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
