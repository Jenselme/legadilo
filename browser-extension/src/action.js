document.addEventListener("DOMContentLoaded", async () => {
  const port = browser.runtime.connect({ name: "legadilo-popup" });
  port.onMessage.addListener(onMessage);

  hideErrorMessage();

  const tab = await getCurrentTab();
  const scriptResult = await browser.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => document.documentElement.outerHTML,
  });
  const pageContent = scriptResult[0].result;

  port.postMessage({
    request: "save-article",
    payload: { link: tab.url, title: tab.title, content: pageContent },
  });
});

/**
 * @param msg {MediaQueryList}
 */
const onMessage = (event) => {
  if (event.error) {
    displayErrorMessage(event.error);
  }

  switch (event.request) {
    case "saved-article":
      savedArticleSuccess(event.article);
      break;
  }
};

const displayErrorMessage = (message) => {
  document.querySelector("#error-message").innerText = message;
  document.querySelector("#error-container").style.display = "block";
};

const hideErrorMessage = () => {
  document.querySelector("#error-container").style.display = "none";
};

/**
 * @returns {Promise<tabs.Tab>}
 */
const getCurrentTab = () =>
  browser.tabs.query({ currentWindow: true, active: true }).then((tabs) => tabs[0]);

const savedArticleSuccess = (article) => {
  hideErrorMessage();

  document.querySelector("#saved-article-title").value = article.title;
};
