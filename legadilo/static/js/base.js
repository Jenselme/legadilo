(function () {
  const setupHtmxConfirmWithPopup = () => {
    document.addEventListener("htmx:confirm", (htmxEvent) => {
      const modalId = htmxEvent.target.dataset.modalId;
      if (!modalId) {
        return;
      }

      htmxEvent.preventDefault();
      const modalTitle = htmxEvent.target.dataset.modalTitle;
      const modalBody = htmxEvent.target.dataset.modalBody;
      const dialogElt = document.getElementById(modalId);
      dialogElt.setAttribute("aria-labelledby", modalTitle);
      dialogElt.querySelector(".modal-title").textContent = modalTitle;
      dialogElt.querySelector(".modal-body").textContent = modalBody;

      const bsModal = new bootstrap.Modal(dialogElt);

      const proceedButton = dialogElt.querySelector("button.proceed");
      const handleProceed = () => {
        bsModal.hide();
        htmxEvent.detail.issueRequest(true);
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

  window.addEventListener("DOMContentLoaded", setupHtmxConfirmWithPopup);
})();
