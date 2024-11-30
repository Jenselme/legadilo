import { saveArticle } from "./legadilo.js";

let extPort;
browser.runtime.onConnect.addListener(function (port) {
  extPort = port;
  port.onMessage.addListener(onMessage);
});

/**
 * @param msg {MediaQueryList}
 */
const onMessage = async (msg) => {
  switch (msg.request) {
    case "save-article":
      try {
        const article = await saveArticle(msg.payload);
        extPort.postMessage({ request: "saved-article", article });
      } catch (err) {
        extPort.postMessage({ error: err.message });
      }
      break;
  }
};
