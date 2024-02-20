const map = L.map('map', { zoomControl: false }).setView([41.90, 12.49], 3, { zoomControl: false });
const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
const trails = new Map();
const hiddenDevices = new Set();
const markers = {};
const devicesContainer = document.getElementById("devices");

async function updateMarkers() {
  return fetch('/api/db/latest')
    .then(response => response.json())
    .then(data => {
      data.forEach(item => {
        const marker = markers[item.id];
        if (marker) {
          marker.setLatLng([item.latitude, item.longitude]);
          marker.setPopupContent(`
            <h2>${item.name}</h2>
            <p>${item.address}</p>
            <p>${item.ago}</p>
          `);
        } else {
          markers[item.id] = L.marker([item.latitude, item.longitude], {
            icon: L.divIcon({
              className: 'device-marker',
              html: !item.image
                ? `<span>${item.icon}</span>`
                : `<img src="${item.image}" alt="device" />`,
              popupAnchor: [0, -20],
              iconSize: [40, 40]
            })
          });

          markers[item.id].addTo(map);
          markers[item.id].bindPopup(`
            <h2>${item.name}</h2>
            <p>${item.address}</p>
            <p>${item.ago}</p>
          `);

          if (!hiddenDevices.has(item.id))
            map.addLayer(markers[item.id]);
        }

        const existingDeviceContainer = document.getElementById(item.id);
        if (existingDeviceContainer) {
          existingDeviceContainer.getElementsByTagName("h3")[0].innerHTML = item.name;
          existingDeviceContainer.getElementsByTagName("p")[0].innerHTML = item.address;
          existingDeviceContainer.getElementsByTagName("p")[1].innerHTML = item.ago;
        } else {
          const createdDeviceContainer = document.createElement("div");
          createdDeviceContainer.id = item.id;
          createdDeviceContainer.className = "device";
          createdDeviceContainer.innerHTML = `
            ${!item.image
              ? `<span>${item.icon}</span>`
              : `<img src="${item.image}" alt="device" />`
            }
            <div>
              <h3 class="center" id="name">${item.name}</h2>
              <p id="address">${item.address}</p>
              <p id="ago">${item.ago}</p>
            </div>
          `;

          devicesContainer.appendChild(createdDeviceContainer);

          createdDeviceContainer.addEventListener('contextmenu', e => {
            e.preventDefault();
            toggleDeviceVisibility(item.id);
          });

          createdDeviceContainer.addEventListener('click', () => {
            const marker = markers[item.id];

            map.flyTo(marker.getLatLng(), 12, { duration: 0.25 });
            marker.openPopup();
          });
        }
      });
    });
}

function toggleAllDevicesVisibility() {
  Object.keys(markers).forEach(id => toggleDeviceVisibility(id));
}

function toggleDeviceVisibility(id) {
  const listItem = document.getElementById(id);
  const trail = trails.get(id);

  if (!trail || !listItem)
    return;

  listItem.classList.toggle('hidden');

  if (hiddenDevices.has(id)) {
    hiddenDevices.delete(id);
    map.addLayer(trail);
    map.addLayer(markers[id]);
  } else {
    hiddenDevices.add(id);
    map.removeLayer(trail);
    map.removeLayer(markers[id]);
  }
}

function createItemsTrail() {
  const allItemsLocations = new Map();
  const promises = [];

  for (const device of document.getElementsByClassName('device')) {
    promises.push(fetch(`/api/db/trail/${device.id}`)
      .then(response => response.json())
      .then(data => {
        const locations = data.map(item => [item.latitude, item.longitude]);

        allItemsLocations.set(device.id, locations);
      }));
  }

  Promise.all(promises).then(() => {
    trails.forEach((trail, _) => {
      map.removeLayer(trail);
    });

    allItemsLocations.forEach((locations, id) => {
      const sortedLocations = locations.sort((a, b) => a.timestamp - b.timestamp);
      const polyline = L.polyline([], {
        color: 'red'
      });

      polyline.setLatLngs(sortedLocations);
      
      if (!hiddenDevices.has(id))
        polyline.addTo(map);

      trails.set(id, polyline);
    });
  });
}

document.addEventListener('DOMContentLoaded', () => {
  const updateAll = () => updateMarkers().then(createItemsTrail);

  setInterval(updateAll, 10000);
  updateAll();

  const title = document.querySelector('#devices-list h1');
  if (!title)
    return;
  title.addEventListener('click', toggleAllDevicesVisibility);
});
