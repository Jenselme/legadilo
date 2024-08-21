document.addEventListener("DOMContentLoaded", function () {
  if (typeof browser === "undefined" && typeof chrome === "object") {
    browser = chrome;
  }
});
