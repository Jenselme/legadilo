/**
 * This is required to both open the article (HTMX will prevent the default action on links) and
 * allow HTMX to mark the article as opened.
 */
(function () {
  "use strict";

  let jsCfg = {};

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

    scrollableContainer.addEventListener("scrollend", readOnScroll);
  };

  const readOnScroll = () => {
    for (const htmxForm of document.querySelectorAll(".readable-on-scroll")) {
      const parentBoundingRect = htmxForm.parentElement.getBoundingClientRect();
      const wasScrolledTo = parentBoundingRect.top < 0;
      const wasScrolledEnough = parentBoundingRect.top < -parentBoundingRect.height / 2;
      if (!wasScrolledTo || !wasScrolledEnough) {
        return;
      }

      htmx.trigger(htmxForm, "submit");
    }
  };

  window.addEventListener("DOMContentLoaded", () => {
    jsCfg = JSON.parse(document.head.querySelector("#js-cfg").textContent);
    setupReadAction();
    setupReadOnScroll();
  });
})();
