function ecoPhotoFailed(image) {
  image.onerror = null;
  const backup = JSON.parse(image.dataset.backup || 'null');
  const container = image.closest('figure') || image.parentElement;
  if (!backup || image.dataset.backupUsed) {
    image.hidden = true;
    return;
  }
  image.dataset.backupUsed = 'true';
  image.onerror = () => { image.hidden = true; };
  image.src = backup.src;
  image.alt = 'Imagen referencial: ' + backup.nombre_confirmado;
  let label = container.querySelector('.visual-label');
  if (!label) {
    label = document.createElement(container.tagName === 'FIGURE' ? 'figcaption' : 'p');
    label.className = 'visual-label';
    container.appendChild(label);
  }
  label.textContent = backup.reference_label || 'Imagen referencial';
  const credit = document.getElementById('credit-' + image.dataset.visualId);
  if (credit) {
    credit.textContent = 'Referencia: ' + backup.nombre_confirmado + '. Foto: ' + backup.autor + ' · ';
    const source = document.createElement('a');
    source.href = backup.fuente_url;
    source.target = '_blank'; source.rel = 'noopener'; source.textContent = 'Fuente';
    credit.appendChild(source);
    credit.appendChild(document.createTextNode(' · ' + backup.licencia));
  }
}
