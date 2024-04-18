if (!window.legadilo) {
  window.legadilo = {};
}

window.legadilo.runArticleUpdateAction = function (actionUrl) {
  const csrftoken = document.querySelector("[name=csrfmiddlewaretoken]").value;
  fetch(actionUrl, {
    method: "POST",
    headers: { "X-CSRFToken": csrftoken },
    mode: "same-origin",
  });
};
