import Tags from "./vendor/tags.js";

let port;
let tagInstance = null;

document.addEventListener("DOMContentLoaded", async () => {
  port = browser.runtime.connect({ name: "legadilo-popup" });
  port.onMessage.addListener(onMessage);

  hideErrorMessage();
  hideArticle();
  displayLoader();

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
const onMessage = async (event) => {
  if (event.error) {
    hideLoader();
    displayErrorMessage(event.error);
    return;
  }

  hideErrorMessage();
  hideLoader();
  switch (event.request) {
    case "saved-article":
      savedArticleSuccess(event.article, event.tags);
      break;
    case "updated-article":
      updatedArticleSuccess(event.article, event.tags);
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

const displayLoader = () => {
  document.querySelector("#loading-indicator-container").style.display = "block";
};

const hideLoader = () => {
  document.querySelector("#loading-indicator-container").style.display = "none";
};

const displayArticle = (article, tags) => {
  document.querySelector("#article-container").style.display = "block";

  if (!article) {
    return;
  }

  document.querySelector("#saved-article-title").value = article.title;
  document.querySelector("#saved-article-reading-time").value = article.reading_time;

  if (tagInstance === null && tags !== undefined && tags !== null) {
    tagInstance = Tags.init("#saved-article-tags", {
      allowNew: true,
      allowClear: true,
      items: tags.reduce((acc, tag) => ({ ...acc, [tag.slug]: tag.title }), {}),
      selected: article.tags.map((tag) => tag.slug),
    });
  }

  if (article.is_read) {
    document.querySelector("#mark-article-as-read").style.display = "none";
    document.querySelector("#mark-article-as-unread").style.display = "block";
  } else {
    document.querySelector("#mark-article-as-read").style.display = "block";
    document.querySelector("#mark-article-as-unread").style.display = "none";
  }
  if (article.is_favorite) {
    document.querySelector("#mark-article-as-favorite").style.display = "none";
    document.querySelector("#unmark-article-as-favorite").style.display = "block";
  } else {
    document.querySelector("#mark-article-as-favorite").style.display = "block";
    document.querySelector("#unmark-article-as-favorite").style.display = "none";
  }
  if (article.is_for_later) {
    document.querySelector("#mark-article-as-for-later").style.display = "none";
    document.querySelector("#unmark-article-as-for-later").style.display = "block";
  } else {
    document.querySelector("#mark-article-as-for-later").style.display = "block";
    document.querySelector("#unmark-article-as-for-later").style.display = "none";
  }
};

const hideArticle = () => {
  document.querySelector("#article-container").style.display = "none";
};

/**
 * @returns {Promise<tabs.Tab>}
 */
const getCurrentTab = () =>
  browser.tabs.query({ currentWindow: true, active: true }).then((tabs) => tabs[0]);

const savedArticleSuccess = (article, tags) => {
  displayArticle(article, tags);
  setupArticleActions(article.id);
};

const setupArticleActions = (articleId) => {
  document.querySelector("#update-saved-article-form").addEventListener("submit", (event) => {
    event.preventDefault();

    const data = new FormData(event.target);

    updateArticle({
      title: data.get("title"),
      tags: data.getAll("tags"),
      readingTime: data.get("reading-time"),
    });
  });

  document.querySelector("#mark-article-as-read").addEventListener("click", () => {
    updateArticle({ readAt: new Date().toISOString() });
  });
  document.querySelector("#mark-article-as-unread").addEventListener("click", () => {
    updateArticle({ readAt: null });
  });
  document.querySelector("#mark-article-as-favorite").addEventListener("click", () => {
    updateArticle({ isFavorite: true });
  });
  document.querySelector("#unmark-article-as-favorite").addEventListener("click", () => {
    updateArticle({ isFavorite: false });
  });
  document.querySelector("#mark-article-as-for-later").addEventListener("click", () => {
    updateArticle({ isForLater: true });
  });
  document.querySelector("#unmark-article-as-for-later").addEventListener("click", () => {
    updateArticle({ isForLater: false });
  });

  const updateArticle = (payload) => {
    hideArticle();
    displayLoader();
    port.postMessage({
      request: "update-article",
      articleId,
      payload,
    });
  };
};

const updatedArticleSuccess = (article, tags) => {
  displayArticle(article, tags);
};
