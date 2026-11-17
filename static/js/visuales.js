function ecoPhotoFailed(image) {
  image.onerror = null;
  image.hidden = true;
  const label = image.closest("figure").querySelector("figcaption");
  label.hidden = false;
  const credit = document.getElementById("credit-" + image.dataset.visualId);
  if (credit) credit.hidden = true;
  const pending = document.getElementById("fotos-pendientes");
  if (pending && !Array.from(pending.children).some(row => row.dataset.pendingId === image.dataset.visualId)) {
    const row = document.createElement("li");
    row.dataset.pendingId = image.dataset.visualId;
    row.textContent = image.dataset.name + " · URL de fotografía no disponible";
    pending.appendChild(row);
    const panel = pending.closest("details");
    panel.hidden = false;
    panel.querySelector(".pending-count").textContent = pending.children.length;
  }
}
