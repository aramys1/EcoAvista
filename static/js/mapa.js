(() => {
  const mapElement = document.getElementById("map");
  const points = window.ecoAvistaMapPoints || [];
  if (!mapElement || typeof L === "undefined") return;

  const map = L.map(mapElement, { scrollWheelZoom: false });
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19
  }).addTo(map);

  const markers = points.map((point) => {
    const marker = L.marker([point.lat, point.lng]).addTo(map);
    const link = document.createElement("a");
    link.href = point.url;
    link.textContent = point.name;
    marker.bindPopup(link);
    return marker;
  });

  if (markers.length === 1) {
    map.setView(markers[0].getLatLng(), 11);
  } else if (markers.length > 1) {
    map.fitBounds(L.featureGroup(markers).getBounds().pad(0.18));
  } else {
    map.setView([8.7, -80.0], 7);
  }
})();
