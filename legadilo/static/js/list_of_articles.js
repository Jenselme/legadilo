/**
 * This is required to both open the article (HTMX will prevent the default action on links) and
 * allow HTMX to mark the article as opened.
 */
(function () {
  "use strict";

  let jsCfg = {};
  let readOnScrollSequence = Promise.resolve();

  const debounce = (fn, waitTime) => {
    let timeout = null;
    return () => {
      if (timeout !== null) {
        clearTimeout(timeout);
      }

      timeout = setTimeout(() => fn(), waitTime);
    };
  };

  const setupReadAction = () => {
    for (const openOriginalButton of document.querySelectorAll(".open-original")) {
      openOriginalButton.addEventListener("click", openAndMarkAsRead);
      openOriginalButton.addEventListener("auxclick", openAndMarkAsRead);
    }
  };

  const openAndMarkAsRead = (event) => {
    const articleId = event.currentTarget.dataset.articleId;
    const htmxForm = document.querySelector(`#mark-article-as-opened-form-${articleId}`);
    if (htmxForm) {
      htmx.trigger(htmxForm, "submit");
      event.currentTarget.removeEventListener("click", openAndMarkAsRead);
      event.currentTarget.removeEventListener("auxclick", openAndMarkAsRead);
    }
  };

  const setupReadOnScroll = () => {
    if (!jsCfg.is_reading_on_scroll_enabled) {
      return;
    }

    const scrollableContainer = document.querySelector("#scrollable-article-list");
    if (!scrollableContainer) {
      return;
    }

    const readOnScrollDebounced = debounce(readOnScroll, 1000);
    // On desktop, we scroll within the container.
    scrollableContainer.addEventListener("scrollend", readOnScrollDebounced);
    // On mobile, we scroll on the document to have more room for articles.
    document.addEventListener("scrollend", readOnScrollDebounced);
  };

  const readOnScroll = () => {
    for (const htmxForm of document.querySelectorAll(".readable-on-scroll")) {
      const parentBoundingRect = htmxForm.parentElement.getBoundingClientRect();
      const wasScrolledTo = parentBoundingRect.top < 0;
      const wasScrolledEnough = parentBoundingRect.top < -parentBoundingRect.height / 2;
      if (!wasScrolledTo || !wasScrolledEnough) {
        return;
      }

      // To make sure counters are correct at the end, we run the requests on after the other so the
      // last one to complete has the correct count.
      readOnScrollSequence = readOnScrollSequence.then(() => buildReadOnScrollPromise(htmxForm));
    }
  };

  const buildReadOnScrollPromise = (htmxForm) => {
    return new Promise((resolve) => {
      const waitForRequestEnd = (event) => {
        if (
          event.detail &&
          event.detail.pathInfo &&
          event.detail.pathInfo.requestPath === htmxForm.getAttribute("action")
        ) {
          htmx.off("htmx:afterRequest", waitForRequestEnd);
          resolve();
        }
      };
      htmx.on("htmx:afterRequest", waitForRequestEnd);
      htmx.trigger(htmxForm, "submit");
    });
  };

  const setupRefresh = () => {
    if (
      !Number.isInteger(jsCfg.auto_refresh_interval) ||
      jsCfg.auto_refresh_interval < jsCfg.articles_list_min_refresh_timeout
    ) {
      return;
    }

    const timeout = jsCfg.auto_refresh_interval * 1000;
    let timeoutId = null;

    const runRefresh = () => {
      if (timeoutId !== null) {
        clearTimeout(timeoutId);
      }

      timeoutId = setTimeout(() => {
        // For desktop.
        const scrollable = document.querySelector(".scrollable");
        if (scrollable) {
          scrollable.scrollTo(0, 0);
        }
        // For mobile.
        window.scroll(0, 0);

        location.reload();
      }, timeout);
    };

    runRefresh();
    // Reset after each scrollend: we want to avoid messing up with reading.
    window.addEventListener("scrollend", runRefresh);
  };

  window.addEventListener("DOMContentLoaded", () => {
    jsCfg = JSON.parse(document.head.querySelector("#js-cfg").textContent);
    setupReadAction();
    setupReadOnScroll();
    setupRefresh();
  });
})();
