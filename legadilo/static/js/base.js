(function () {
  const setupHtmxConfirmWithPopup = () => {
    document.addEventListener("htmx:confirm", (htmxEvent) => {
      const elementForModal = getElementForModalData(htmxEvent);
      if (!elementForModal) {
        return;
      }

      const modalId = elementForModal.dataset.modalId;
      if (!modalId) {
        return;
      }

      htmxEvent.preventDefault();
      const modalTitle = elementForModal.dataset.modalTitle;
      const modalBody = elementForModal.dataset.modalBody;
      const dialogElt = document.getElementById(modalId);
      dialogElt.setAttribute("aria-labelledby", modalTitle);
      dialogElt.querySelector(".modal-title").textContent = modalTitle;
      dialogElt.querySelector(".modal-body").textContent = modalBody;

      const bsModal = new bootstrap.Modal(dialogElt);

      const proceedButton = dialogElt.querySelector("button.proceed");
      const handleProceed = () => {
        bsModal.hide();
        // When we use HTMX confirm, HTMX will lose the last button clicked and thus won't transmit
        // its name. It's a problem. In which case, we force it ourselves with the hx-vals attribute.
        // To avoid having multiple names in other cases (and thus interfering with form actions)
        // we remove it afterward.
        if (
          htmxEvent.explicitOriginalTarget &&
          htmxEvent.explicitOriginalTarget.getAttribute("name")
        ) {
          const buttonName = htmxEvent.explicitOriginalTarget.getAttribute("name");
          htmxEvent.target.setAttribute("hx-vals", JSON.stringify({ [buttonName]: "" }));
        }
        htmxEvent.detail.issueRequest(true);
        htmxEvent.target.removeAttribute("hx-vals");
      };
      const handleClose = () => {
        dialogElt.removeEventListener("hide.bs.modal", handleClose);
        proceedButton.removeEventListener("click", handleProceed);
      };

      dialogElt.addEventListener("hide.bs.modal", handleClose);
      proceedButton.addEventListener("click", handleProceed);
      bsModal.show();
    });
  };

  const getElementForModalData = (htmxEvent) => {
    // By default, we look at the form, but sometimes we only want confirmation on a certain button.
    // In which case, we want to put the data-* attribute for the modal on it directly.
    if (htmxEvent.target.dataset.modalId) {
      return htmxEvent.target;
    }

    if (htmxEvent.explicitOriginalTarget.dataset.modalId) {
      return htmxEvent.explicitOriginalTarget;
    }
  };

  let tooltips = [];
  const setupTooltips = () => {
    tooltips.forEach((tooltip) => tooltip.dispose());

    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips = [...tooltipTriggerList].map((tooltipTriggerEl) => {
      return new bootstrap.Tooltip(tooltipTriggerEl);
    });
  };

  window.addEventListener("DOMContentLoaded", setupHtmxConfirmWithPopup);
  window.addEventListener("DOMContentLoaded", setupTooltips);
  window.addEventListener("htmx:afterOnLoad", setupTooltips);
})();
