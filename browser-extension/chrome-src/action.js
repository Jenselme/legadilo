import Tags from "./vendor/tags.js";

let articleTagsInstance = null;
let feedTagsInstance = null;

document.addEventListener("DOMContentLoaded", async () => {
  hideLoader();
  hideErrorMessage();
  hideActionSelector();
  hideArticle();
  hideFeed();

  const tab = await getCurrentTab();
  const scriptResult = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => document.documentElement.outerHTML,
  });
  const pageContent = scriptResult[0].result;

  runDefaultAction(tab, pageContent);
});

const runDefaultAction = (tab, pageContent) => {
  const parser = new DOMParser();
  const htmlDoc = parser.parseFromString(pageContent, "text/html");
  const feedNodes = [];
  feedNodes.push(...htmlDoc.querySelectorAll('[type="application/rss+xml"]'));
  feedNodes.push(...htmlDoc.querySelectorAll('[type="application/atom+xml"]'));

  // No feed links, let's save immediately.
  if (feedNodes.length === 0) {
    saveArticle(tab, pageContent);
    return;
  }

  displayActionSelector(tab, pageContent, feedNodes);
};

const onResponse = (request) => {
  if (request.error) {
    hideLoader();
    displayErrorMessage(request.error);
    return;
  }

  hideErrorMessage();
  hideLoader();
  switch (request.name) {
    case "saved-article":
      savedArticleSuccess(request.article, request.tags);
      break;
    case "updated-article":
      updatedArticleSuccess(request.article, request.tags);
      break;
    case "subscribed-to-feed":
      feedSubscriptionSuccess(request.feed, request.tags, request.categories);
      break;
    case "updated-feed":
      updatedFeedSuccess(request.feed, request.tags, request.categories);
      break;
    default:
      console.warn(`Unknown action ${request.name}`);
  }
};

const displayActionSelector = (tab, pageContent, feedNodes) => {
  document.querySelector("#action-selector-container").style.display = "block";

  const chooseFeedsContainer = document.querySelector("#choose-action-container");
  for (const feedNode of feedNodes) {
    const button = document.createElement("button");
    button.classList.add("btn", "btn-outline-primary", "mb-2", "col");
    button.innerText = feedNode.getAttribute("title");
    let feedHref = feedNode.getAttribute("href");
    if (feedHref.startsWith("//")) {
      const pageProtocol = new URL(tab.url).protocol;
      feedHref = `${pageProtocol}${feedHref}`;
    }
    button.addEventListener("click", () => {
      hideActionSelector();
      subscribeToFeed(feedHref);
    });
    chooseFeedsContainer.appendChild(button);
  }

  document.querySelector("#save-article-action-btn").addEventListener("click", () => {
    hideActionSelector();
    saveArticle(tab, pageContent);
  });
};

const hideActionSelector = () => {
  document.querySelector("#action-selector-container").style.display = "none";
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

  document.querySelector("#saved-article-title").value = article.title;
  document.querySelector("#saved-article-reading-time").value = article.reading_time;

  if (articleTagsInstance === null) {
    articleTagsInstance = Tags.init("#saved-article-tags", {
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

const displayFeed = (feed, tags, categories) => {
  document.querySelector("#feed-container").style.display = "block";
  document.querySelector("#feed-title").innerText = feed.title;

  document.querySelector("#feed-refresh-delay").value = feed.refresh_delay;
  document.querySelector("#feed-article-retention-time").value = feed.article_retention_time;

  const categorySelector = document.querySelector("#feed-category");
  // Clean all existing choices.
  categorySelector.innerHTML = "";
  const noCategoryOption = document.createElement("option");
  noCategoryOption.value = "";
  noCategoryOption.innerText = "No Category";
  categorySelector.appendChild(noCategoryOption);
  for (const category of categories) {
    const option = document.createElement("option");
    option.value = category.id;
    option.innerText = category.title;
    categorySelector.appendChild(option);
  }
  categorySelector.value = feed.category ? feed.category.id : "";

  if (feedTagsInstance === null) {
    feedTagsInstance = Tags.init("#feed-tags", {
      allowNew: true,
      allowClear: true,
      items: tags.reduce((acc, tag) => ({ ...acc, [tag.slug]: tag.title }), {}),
      selected: feed.tags.map((tag) => tag.slug),
    });
  }

  document.querySelector("#update-feed-form").addEventListener("submit", async (event) => {
    event.preventDefault();

    const data = new FormData(event.target);

    hideFeed();
    displayLoader();
    const response = await chrome.runtime.sendMessage({
      name: "update-feed",
      feedId: feed.id,
      payload: {
        categoryId: data.get("category") || null,
        refreshDelay: data.get("refresh-delay"),
        articleRetentionTime: data.get("retention-time"),
        tags: data.getAll("tags"),
      },
    });

    onResponse(response);
  });
};

const hideFeed = () => {
  document.querySelector("#feed-container").style.display = "none";
};

/**
 * @returns {Promise<tabs.Tab>}
 */
const getCurrentTab = () =>
  chrome.tabs.query({ currentWindow: true, active: true }).then((tabs) => tabs[0]);

const saveArticle = async (tab, pageContent) => {
  displayLoader();
  const response = await chrome.runtime.sendMessage({
    name: "save-article",
    payload: { link: tab.url, title: tab.title, content: pageContent },
  });

  onResponse(response);
};

const savedArticleSuccess = (article, tags) => {
  console.log("anuierta unriteanurit n");
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

  const updateArticle = async (payload) => {
    hideArticle();
    displayLoader();
    const response = await chrome.runtime.sendMessage({
      name: "update-article",
      articleId,
      payload,
    });

    onResponse(response);
  };
};

const updatedArticleSuccess = (article, tags) => {
  displayArticle(article, tags);
};

const subscribeToFeed = async (link) => {
  displayLoader();
  const response = await chrome.runtime.sendMessage({
    name: "subscribe-to-feed",
    payload: { link },
  });

  onResponse(response);
};

const feedSubscriptionSuccess = (feed, tags, categories) => {
  displayFeed(feed, tags, categories);
};

const updatedFeedSuccess = (feed, tags, categories) => {
  displayFeed(feed, tags, categories);
};
