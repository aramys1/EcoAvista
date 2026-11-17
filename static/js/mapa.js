(() => {
  const element = document.getElementById("map");
  const status = document.getElementById("map-status");
  const points = window.ecoAvistaMapPoints || [];
  if (!element) return;
  const warn = (message) => { status.hidden = false; status.textContent = message; };
  if (typeof L === "undefined") {
    warn("No se pudo cargar Leaflet. Consulta la lista de lugares; el mapa requiere Internet.");
    element.hidden = true;
    return;
  }
  try {
    const map = L.map(element, { scrollWheelZoom: false });
    const tiles = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors', maxZoom: 19
    });
    let loaded = false;
    let failed = false;
    const timeout = setTimeout(() => {
      if (!loaded) warn("El mapa base tarda en cargar. La lista de lugares sigue disponible más abajo.");
    }, 10000);
    tiles.on("tileload", () => { loaded = true; clearTimeout(timeout); if (!failed) status.hidden = true; });
    tiles.on("tileerror", () => {
      failed = true;
      warn("No se pudo cargar parte del mapa base de OpenStreetMap. Consulta también la lista de lugares.");
    });
    tiles.addTo(map);
    const markers = points.map((point) => {
      const color = point.centroid ? "#24734b" : "#236c91";
      const marker = L.circleMarker([point.lat, point.lng], { radius: 7, color, fillColor: color, fillOpacity: 0.8 }).addTo(map);
      const content = document.createElement("div");
      const link = document.createElement("a");
      link.href = point.url;
      link.textContent = point.name;
      content.appendChild(link);
      [point.category, point.coordinateType, "No es una entrada ni la ubicación de una especie."].forEach((text) => {
        const paragraph = document.createElement("p"); paragraph.textContent = text; content.appendChild(paragraph);
      });
      marker.bindPopup(content);
      return marker;
    });
    if (markers.length) map.fitBounds(L.featureGroup(markers).getBounds().pad(0.12), { maxZoom: 11 });
  } catch (error) {
    warn("No se pudo iniciar el mapa. La lista de lugares permanece disponible más abajo.");
    element.hidden = true;
  }
})();
