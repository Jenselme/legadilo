import Tags from "./vendor/tags.js";
import { listArticles, listEnabledFeeds } from "./legadilo.js";

let port;
let articleTagsInstance = null;
let feedTagsInstance = null;

const isFirefox = typeof browser === "object";

document.addEventListener("DOMContentLoaded", () => {
  connectToPort();

  hideLoader();
  hideErrorMessage();
  hideActionSelector();
  hideArticle();
  hideFeed();

  runDefaultAction();
});

const connectToPort = () => {
  if (!isFirefox) {
    return null;
  }

  port = chrome.runtime.connect({ name: "legadilo-popup" });
  port.onMessage.addListener(onMessage);
};

const runDefaultAction = async () => {
  const tab = await getCurrentTab();
  const pageContent = await getPageContent(tab);
  const feedNodes = getFeedNodes(pageContent);

  // No feed links, let's save immediately.
  if (feedNodes.length === 0) {
    await saveArticle(tab, pageContent);
    return;
  }

  await displayActionsSelector();
};

const getFeedNodes = (pageContent) => {
  const parser = new DOMParser();
  const htmlDoc = parser.parseFromString(pageContent, "text/html");
  const feedNodes = [];
  feedNodes.push(...htmlDoc.querySelectorAll('[type="application/rss+xml"]'));
  feedNodes.push(...htmlDoc.querySelectorAll('[type="application/atom+xml"]'));

  return feedNodes;
};

const getCanonicalUrl = (tab, pageContent) => {
  const parser = new DOMParser();
  const htmlDoc = parser.parseFromString(pageContent, "text/html");

  const canonicalLink = htmlDoc.querySelector("link[rel='canonical']");
  if (!canonicalLink) {
    return null;
  }

  return buildFullUrl(tab, canonicalLink.getAttribute("href"));
};

const onMessage = (request) => {
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
    case "deleted-article":
      displayActionsSelector();
      break;
    case "subscribed-to-feed":
      feedSubscriptionSuccess(request.feed, request.tags, request.categories);
      break;
    case "updated-feed":
      updatedFeedSuccess(request.feed, request.tags, request.categories);
      break;
    case "deleted-feed":
      displayActionsSelector();
      break;
    default:
      console.warn(`Unknown action ${request.name}`);
  }
};

const displayActionsSelector = async () => {
  displayLoader();
  const tab = await getCurrentTab();
  const pageContent = await getPageContent(tab);
  const feedNodes = getFeedNodes(pageContent);
  const feedUrls = feedNodes.map((feedNode) => getFeedHref(tab, feedNode));
  const articleUrls = [tab.url];
  const articleCanonicalUrl = getCanonicalUrl(tab, pageContent);
  if (articleCanonicalUrl) {
    articleUrls.push(articleCanonicalUrl);
  }
  const savedArticles = (await listArticles({ articleUrls })).items;
  const subscribedFeedUrls = (await listEnabledFeeds({ feedUrls })).items.map(
    (feed) => feed.feed_url,
  );
  hideLoader();

  const articleAlreadySaved = document.querySelector("#article-already-saved");
  if (savedArticles.length > 0) {
    articleAlreadySaved.style.display = "inline";
  } else {
    articleAlreadySaved.style.display = "none";
  }

  document.querySelector("#action-selector-container").style.display = "block";

  const chooseFeedsContainer = document.querySelector("#subscribe-to-feeds-container");
  chooseFeedsContainer.replaceChildren();

  for (const feedNode of feedNodes) {
    let feedHref = getFeedHref(tab, feedNode);

    const button = document.createElement("button");
    button.classList.add("btn", "btn-outline-primary", "mb-2", "col");
    let feedTitle = feedNode.getAttribute("title");
    if (!feedTitle) {
      const hostname = new URL(tab.url).hostname;
      const type = feedNode.getAttribute("type");
      const feedType = type.replace("application/", "").replace("+xml", "");
      feedTitle = `${hostname} (${feedType})`;
    }

    button.innerHTML = `${feedTitle} ${
      subscribedFeedUrls.includes(feedHref)
        ? '<img class="bi" src="./vendor/bs-icons/rss-fill.svg" alt="Already subscribed to this feed" />'
        : ""
    }`;

    button.addEventListener("click", () => {
      hideActionSelector();
      subscribeToFeed(feedHref);
    });
    chooseFeedsContainer.appendChild(button);
  }

  document.querySelector("#save-article-action-btn").addEventListener("click", async () => {
    hideActionSelector();
    await saveArticle(tab, pageContent);
  });
};

const getFeedHref = (tab, feedNode) => {
  let feedHref = feedNode.getAttribute("href");
  feedHref = buildFullUrl(tab, feedHref);

  return feedHref;
};

const buildFullUrl = (tab, url) => {
  if (/^https?:\/\//.test(url)) {
    return url;
  }

  if (url.startsWith("//")) {
    const pageProtocol = new URL(tab.url).protocol;
    return `${pageProtocol}${url}`;
  }

  const origin = new URL(tab.url).origin;
  return `${origin}${url}`;
};

const hideActionSelector = () => {
  document.querySelector("#action-selector-container").style.display = "none";
};

const errorNavBack = async () => {
  hideErrorMessage();
  await displayActionsSelector();
  document.querySelector("#error-nav-back").removeEventListener("click", errorNavBack);
};

const displayErrorMessage = (message) => {
  document.querySelector("#error-message").innerText = message;
  document.querySelector("#error-container").style.display = "block";

  document.querySelector("#error-nav-back").addEventListener("click", errorNavBack);
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

const createTagInstance = (element, tags, selectedTags) => {
  const tagsHierarchy = tags.reduce((acc, tag) => ({ ...acc, [tag.slug]: tag.sub_tags }), {});

  return Tags.init(element, {
    allowNew: true,
    allowClear: true,
    items: tags.reduce((acc, tag) => ({ ...acc, [tag.slug]: tag.title }), {}),
    selected: selectedTags.map((tag) => tag.slug),
    onSelectItem(item, instance) {
      if (!Array.isArray(tagsHierarchy[item.value])) {
        return;
      }

      const alreadyAddedItems = instance.getSelectedValues();
      tagsHierarchy[item.value]
        .filter((tag) => !alreadyAddedItems.includes(tag.slug))
        .forEach((tag) => instance.addItem(tag.title, tag.slug));
    },
  });
};

const displayArticle = (article, tags) => {
  document.querySelector("#article-container").style.display = "block";

  document.querySelector("#saved-article-title").value = article.title;
  document.querySelector("#saved-article-reading-time").value = article.reading_time;

  if (articleTagsInstance === null) {
    articleTagsInstance = createTagInstance("#saved-article-tags", tags, article.tags);
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

  document.querySelector("#open-article-details").href = article.details_url;
};

const hideArticle = () => {
  document.querySelector("#article-container").style.display = "none";
};

const displayFeed = (feed, tags, categories) => {
  document.querySelector("#feed-container").style.display = "block";
  document.querySelector("#feed-title").innerText = feed.title;

  document.querySelector("#feed-refresh-delay").value = feed.refresh_delay;
  document.querySelector("#feed-article-retention-time").value = feed.article_retention_time;

  document.querySelector("#open-feed-details").href = feed.details_url;

  if (feed.enabled) {
    document.querySelector("#enable-feed").style.display = "none";
    document.querySelector("#disable-feed").style.display = "block";
  } else {
    document.querySelector("#enable-feed").style.display = "block";
    document.querySelector("#disable-feed").style.display = "none";
  }

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
    feedTagsInstance = createTagInstance("#feed-tags", tags, feed.tags);
  }
};

const setupFeedActions = (feedId) => {
  const updateFeed = (payload) => {
    hideFeed();
    displayLoader();
    sendMessage({
      name: "update-feed",
      feedId: feedId,
      payload,
    });
  };

  const deleteFeed = () => {
    hideFeed();
    displayLoader();
    sendMessage({
      name: "delete-feed",
      feedId,
    });
  };

  const actions = {
    "#update-feed": (event) => {
      event.preventDefault();
      const data = new FormData(document.querySelector("#update-feed-form"));
      updateFeed({
        categoryId: data.get("category") || null,
        refreshDelay: data.get("refresh-delay"),
        articleRetentionTime: data.get("retention-time"),
        tags: data.getAll("tags"),
      });
    },
    "#enable-feed": () => updateFeed({ disabledAt: null, disabledReason: null }),
    "#disable-feed": () =>
      updateFeed({
        disabledAt: new Date().toISOString(),
        disabledReason: "Disable manually in the browser extension",
      }),
    "#delete-feed": () =>
      askConfirmation("Are you sure you want to delete this feed?").then(deleteFeed),
    "#feed-nav-back": async () => {
      Object.entries(actions).forEach(([selector, action]) => {
        document.querySelector(selector).removeEventListener("click", action);
      });

      hideFeed();
      await displayActionsSelector();
    },
  };

  Object.entries(actions).forEach(([selector, action]) => {
    document.querySelector(selector).addEventListener("click", action);
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

const getPageContent = async (tab) => {
  const scriptResult = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => document.documentElement.outerHTML,
  });
  return scriptResult[0].result;
};

const saveArticle = (tab, pageContent) => {
  displayLoader();
  sendMessage({
    name: "save-article",
    payload: { url: tab.url, title: tab.title, content: pageContent },
  });
};

const savedArticleSuccess = (article, tags) => {
  displayArticle(article, tags);
  setupArticleActions(article.id);
};

const setupArticleActions = (articleId) => {
  const updateArticle = (payload) => {
    hideArticle();
    displayLoader();
    sendMessage({
      name: "update-article",
      articleId,
      payload,
    });
  };

  const deleteArticle = () => {
    hideArticle();
    displayLoader();
    sendMessage({
      name: "delete-article",
      articleId,
    });
  };

  const actions = {
    "#update-saved-article": (event) => {
      event.preventDefault();

      const data = new FormData(document.querySelector("#update-saved-article-form"));

      updateArticle({
        title: data.get("title"),
        tags: data.getAll("tags"),
        readingTime: data.get("reading-time"),
      });
    },
    "#mark-article-as-read": () => {
      updateArticle({ readAt: new Date().toISOString() });
    },
    "#mark-article-as-unread": () => {
      updateArticle({ readAt: null });
    },
    "#mark-article-as-favorite": () => {
      updateArticle({ isFavorite: true });
    },
    "#unmark-article-as-favorite": () => {
      updateArticle({ isFavorite: false });
    },
    "#mark-article-as-for-later": () => {
      updateArticle({ isForLater: true });
    },
    "#unmark-article-as-for-later": () => {
      updateArticle({ isForLater: false });
    },
    "#delete-article": () =>
      askConfirmation("Are you sure you want to delete this article?").then(deleteArticle),
    "#article-nav-back": async () => {
      hideArticle();

      Object.entries(actions).forEach(([selector, action]) => {
        document.querySelector(selector).removeEventListener("click", action);
      });

      await displayActionsSelector();
    },
  };

  Object.entries(actions).forEach(([selector, action]) => {
    document.querySelector(selector).addEventListener("click", action);
  });
};

const updatedArticleSuccess = (article, tags) => {
  displayArticle(article, tags);
};

const subscribeToFeed = (link) => {
  displayLoader();
  sendMessage({
    name: "subscribe-to-feed",
    payload: { link },
  });
};

const feedSubscriptionSuccess = (feed, tags, categories) => {
  displayFeed(feed, tags, categories);
  setupFeedActions(feed.id);
};

const updatedFeedSuccess = (feed, tags, categories) => {
  displayFeed(feed, tags, categories);
};

const sendMessage = async (message) => {
  if (isFirefox) {
    port.postMessage(message);
    return;
  }

  const response = await chrome.runtime.sendMessage(message);
  onMessage(response);
};

const askConfirmation = (message) => {
  const confirmDialog = document.getElementById("confirm-dialog");

  const confirmDialogTitle = document.getElementById("confirm-dialog-title");
  confirmDialogTitle.innerText = message;

  let resolveDeferred;
  let rejectDeferred;
  const deferred = new Promise((resolve, reject) => {
    resolveDeferred = resolve;
    rejectDeferred = reject;
  });
  const cancelBtn = document.getElementById("confirm-dialog-cancel-btn");
  const confirmBtn = document.getElementById("confirm-dialog-confirm-btn");
  const cancel = () => {
    confirmDialog.close();
    rejectDeferred();
    cancelBtn.removeEventListener("click", cancel);
    confirmBtn.removeEventListener("click", confirm);
  };
  const confirm = () => {
    confirmDialog.close();
    resolveDeferred();
    cancelBtn.removeEventListener("click", cancel);
    confirmBtn.removeEventListener("click", confirm);
  };

  cancelBtn.addEventListener("click", cancel);
  confirmBtn.addEventListener("click", confirm);

  confirmDialog.showModal();

  return deferred;
};
