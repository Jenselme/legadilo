// Legadilo
// Copyright (C) 2023-2025 by Legadilo contributors.
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.
//
// SPDX-License-Identifier: AGPL-3.0-or-later

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
      console.log("Read on scroll is not enabled for this reading list.");
      return;
    }

    console.log("Setting up read on scroll.");
    // Force a scroll to top after reloading the page: previously read articles won’t be there
    // anymore and the back button of the browser will preserve scroll. We may end up marking some
    // articles as read when we shouldn’t. Clicking the back button on the details page doesn’t have
    // this issue.
    // Note: using the back button of the browser or the back button of the page or a soft refresh
    // correctly triggers the scroll to top code. However, when the browser is reopened, it did not.
    // it seems that the browser is restoring the scroll with a little delay after the scroll to
    // top had run. Hence, this timeout block. Improve this if you have a cleaner solution.
    // We don’t start marking articles as read until the scroll is done: it can take a while and on
    // some occasions, we may start marking articles as read before the scroll is done.
    setTimeout(() => {
      window.scroll(0, 0);
      // Wait before reading on scroll: the user may scroll up again! We don’t want to mark articles
      // as read in this case.
      const readOnScrollDebounced = debounce(readOnScroll, 1_000);
      document.addEventListener("scrollend", readOnScrollDebounced);
      console.log("Read on scroll setup!");
    }, 500);
  };

  const readOnScroll = () => {
    const isReadOnScrollCheckboxTicked = document.getElementById("read-on-scroll-status").checked;

    if (!isReadOnScrollCheckboxTicked) {
      return;
    }

    const articleIdsToMarkAsRead = findArticleIdsToReadOnScroll();

    if (articleIdsToMarkAsRead.length === 0) {
      return;
    }

    // To make sure counters are correct at the end, we run the requests on after the other so the
    // last one to complete has the correct count.
    console.log(`Adding ${articleIdsToMarkAsRead} to the promise chain.`);
    readOnScrollSequence = readOnScrollSequence.then(() =>
      buildReadOnScrollPromise(articleIdsToMarkAsRead),
    );
  };

  const findArticleIdsToReadOnScroll = () => {
    const articleIdsToMarkAsRead = [];
    for (const article of document.querySelectorAll(".readable-on-scroll")) {
      const parentBoundingRect = article.getBoundingClientRect();
      const wasScrolledTo = parentBoundingRect.top < 0;
      const wasScrolledEnough = parentBoundingRect.top < -parentBoundingRect.height / 2;
      if (!wasScrolledTo || !wasScrolledEnough) {
        break;
      }

      articleIdsToMarkAsRead.push(article.dataset.articleId);
    }

    return articleIdsToMarkAsRead;
  };

  const buildReadOnScrollPromise = (articleIdsToMarkAsRead) => {
    console.log(`Previous promise resolved, starting ${articleIdsToMarkAsRead}`);
    const formToSubmit = document.getElementById("bulk-mark-as-read-form");
    return new Promise((resolve) => {
      // Sometimes it can get stuck because of a weird bug in FF. Force a resolution after 10s to
      // try to at least mark the other articles as read. See #195
      const forceResolutionTimer = setTimeout(() => {
        console.log(
          `Request ${articleIdsToMarkAsRead} is taking too much time, forcing resolution`,
        );
        resolve();
      }, 10 * 1000);
      const waitForRequestEnd = (event) => {
        if (
          event.detail &&
          event.detail.pathInfo &&
          event.detail.pathInfo.requestPath === formToSubmit.getAttribute("action")
        ) {
          console.log(`Done for ${articleIdsToMarkAsRead}, resolving promise.`);
          htmx.off("htmx:afterRequest", waitForRequestEnd);
          clearTimeout(forceResolutionTimer);
          resolve();
        }
      };
      document.getElementById("bulk-mark-as-read-data").value = articleIdsToMarkAsRead.join(",");
      htmx.on("htmx:afterRequest", waitForRequestEnd);
      htmx.trigger("#bulk-mark-as-read-form", "submit");
    });
  };

  const setupAutoRefresh = () => {
    const timeout = jsCfg.auto_refresh_interval * 3600 * 1000;
    if (!Number.isInteger(jsCfg.auto_refresh_interval)) {
      return;
    }

    let timeoutId = null;

    const runRefresh = () => {
      if (timeoutId !== null) {
        clearTimeout(timeoutId);
      }

      timeoutId = setTimeout(() => {
        window.scroll(0, 0);
        location.reload();
      }, timeout);
    };

    runRefresh();
    // Reset after each scrollend: we want to avoid messing up with reading.
    window.addEventListener("scrollend", runRefresh);
  };

  const setupMobileScroll = () => {
    const headerHeight = getComputedStyle(document.body).getPropertyValue(
      "--content-header-height",
    );
    const readingListTitleContainer = document.getElementById("reading-list-title-container");
    readingListTitleContainer.style.top = headerHeight;
    const titleHeight = readingListTitleContainer.getBoundingClientRect().height;
    const readingListActionsContainer = document.getElementById("reading-list-actions-container");
    readingListActionsContainer.style.top = `calc(${headerHeight} + ${titleHeight}px)`;

    let currentOffset = window.scrollY;

    window.addEventListener("scroll", () => {
      if (currentOffset > window.scrollY) {
        readingListTitleContainer.classList.add("sticky-top");
        readingListActionsContainer.classList.add("sticky-top");
      } else {
        readingListTitleContainer.classList.remove("sticky-top");
        readingListActionsContainer.classList.remove("sticky-top");
      }

      currentOffset = window.scrollY;
    });
  };

  window.addEventListener("load", () => {
    jsCfg = JSON.parse(document.head.querySelector("#js-cfg").textContent);
    setupReadAction();
    setupReadOnScroll();
    setupAutoRefresh();
    setupMobileScroll();
  });
})();
