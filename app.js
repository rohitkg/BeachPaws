/* Kent Beach Filter — filter logic, list rendering, Leaflet map sync. */
(function () {
  "use strict";

  var MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"];

  var state = {
    sandy: "any",              // any | yes | no
    dog: "any",                // any | yearround | month | banned | unknown
    month: new Date().getMonth() + 1,  // 1-12, used when dog === "month"
    monitored: "any"           // any | yes | no — EA-designated bathing water
  };

  var beaches = [];
  var map, markerLayer;
  var markersById = {};

  /* ---------- date helpers (MM-DD strings, zero-padded) ---------- */

  function pad2(n) { return (n < 10 ? "0" : "") + n; }

  // "05-01" -> "1 May"
  function fmtDate(mmdd) {
    var m = parseInt(mmdd.slice(0, 2), 10);
    var d = parseInt(mmdd.slice(3, 5), 10);
    return d + " " + MONTH_NAMES[m - 1].slice(0, 3);
  }

  // Does month m (1-12) overlap the ban window? Lexical compare on MM-DD.
  function monthOverlapsBan(m, ban) {
    var monthStart = pad2(m) + "-01";
    var monthEnd = pad2(m) + "-31";
    var windows = ban.from <= ban.to
      ? [[ban.from, ban.to]]
      : [[ban.from, "12-31"], ["01-01", ban.to]]; // defensive: year-wrapping window
    return windows.some(function (w) {
      return !(monthEnd < w[0] || monthStart > w[1]);
    });
  }

  /* ---------- filter semantics ---------- */

  // Result: "yes" (include), "no" (exclude), "hours" (include, restricted hours)
  function dogMatch(beach) {
    var dogs = beach.dogs;
    switch (state.dog) {
      case "any": return "yes";
      case "yearround": return dogs.status === "friendly" ? "yes" : "no";
      case "banned": return dogs.status === "banned" ? "yes" : "no";
      case "unknown": return dogs.status === "unknown" ? "yes" : "no";
      case "month":
        if (dogs.status === "friendly") return "yes";
        if (dogs.status === "seasonal") {
          if (!monthOverlapsBan(state.month, dogs.ban)) return "yes";
          return dogs.ban.daily ? "hours" : "no";
        }
        return "no"; // banned or unknown
    }
    return "yes";
  }

  function applyFilters() {
    var visible = [];
    var hiddenUnknown = 0;
    beaches.forEach(function (beach) {
      // Beaches with no EA sediment data only appear under "Any".
      if (state.sandy === "yes" && !beach.sandy) return;
      if (state.sandy === "no" && (beach.sandy || !beach.sediments.length)) return;
      if (state.monitored === "yes" && beach.eaMonitored !== true) return;
      if (state.monitored === "no" && beach.eaMonitored !== false) return;
      var dm = dogMatch(beach);
      if (dm === "no") {
        if (state.dog === "month" && beach.dogs.status === "unknown") hiddenUnknown++;
        return;
      }
      visible.push({ beach: beach, restrictedHours: dm === "hours" });
    });
    renderList(visible, hiddenUnknown);
    renderMarkers(visible);
    var count = document.getElementById("result-count");
    count.textContent = "Showing " + visible.length + " of " + beaches.length + " beaches";
  }

  /* ---------- badges ---------- */

  function makeBadge(text, cls) {
    var span = document.createElement("span");
    span.className = "badge " + cls;
    span.textContent = text;
    return span;
  }

  function dogBadge(beach, restrictedHours) {
    var dogs = beach.dogs;
    if (dogs.status === "friendly") return makeBadge("Dogs welcome year round", "badge-green");
    if (dogs.status === "banned") return makeBadge("No dogs", "badge-red");
    if (dogs.status === "seasonal") {
      var window_ = fmtDate(dogs.ban.from) + "–" + fmtDate(dogs.ban.to);
      if (dogs.ban.daily) {
        var text = "Dogs restricted " + dogs.ban.daily.replace("-", "–") + ", " + window_;
        return makeBadge(text, "badge-amber");
      }
      return makeBadge("No dogs " + window_, restrictedHours ? "badge-amber" : "badge-red");
    }
    return makeBadge("Dog rules unknown", "badge-grey");
  }

  function badgesFor(beach, restrictedHours) {
    var wrap = document.createElement("div");
    wrap.className = "badges";
    if (beach.sandy) {
      wrap.appendChild(makeBadge("Sandy", "badge-sand"));
    } else if (beach.sediments.length) {
      wrap.appendChild(makeBadge("Not sandy", "badge-neutral"));
    } else {
      wrap.appendChild(makeBadge("Sediment unknown", "badge-grey"));
    }
    if (beach.sediments.length) {
      wrap.appendChild(makeBadge(beach.sediments.join(" · "), "badge-neutral"));
    }
    wrap.appendChild(dogBadge(beach, restrictedHours));
    if (beach.waterQuality) {
      wrap.appendChild(makeBadge(
        "Water: " + beach.waterQuality.class + " (" + beach.waterQuality.year + ")",
        "badge-wq-" + beach.waterQuality.class));
    }
    if (beach.eaMonitored === false) {
      wrap.appendChild(makeBadge("Not an EA bathing water", "badge-grey"));
    }
    return wrap;
  }

  /* ---------- list rendering ---------- */

  function renderList(visible, hiddenUnknown) {
    var list = document.getElementById("beach-list");
    list.textContent = "";

    if (!visible.length) {
      var empty = document.createElement("p");
      empty.className = "empty-state";
      empty.textContent = "No beaches match these filters.";
      list.appendChild(empty);
    }

    visible.forEach(function (item) {
      var beach = item.beach;
      var card = document.createElement("article");
      card.className = "beach-card";

      var h2 = document.createElement("h2");
      h2.textContent = beach.name;
      card.appendChild(h2);

      var district = document.createElement("p");
      district.className = "district";
      district.textContent = beach.district +
        (beach.lat === null ? " · location unavailable" : "");
      card.appendChild(district);

      card.appendChild(badgesFor(beach, item.restrictedHours));

      if (beach.dogs.notes) {
        var notes = document.createElement("p");
        notes.className = "notes";
        notes.textContent = beach.dogs.notes;
        card.appendChild(notes);
      }

      if (beach.dogs.source) {
        var source = document.createElement("p");
        source.className = "source";
        var a = document.createElement("a");
        a.href = beach.dogs.source;
        a.rel = "external";
        a.target = "_blank";
        a.textContent = "Dog rules source";
        source.appendChild(a);
        source.appendChild(document.createTextNode(
          " · checked " + beach.dogs.accessed));
        card.appendChild(source);
      }

      card.addEventListener("click", function (ev) {
        if (ev.target.tagName === "A") return; // let source links work
        var marker = markersById[beach.id];
        if (marker) {
          map.panTo(marker.getLatLng());
          marker.openPopup();
        }
      });

      list.appendChild(card);
    });

    if (hiddenUnknown > 0) {
      var note = document.createElement("p");
      note.className = "hidden-note";
      note.textContent = hiddenUnknown +
        " beach(es) with unknown dog rules hidden — select “Unknown rules” to see them.";
      list.appendChild(note);
    }
  }

  /* ---------- map ---------- */

  var STATUS_COLORS = {
    friendly: "#1d6f42",
    seasonal: "#c96a10",
    banned: "#a1261f",
    unknown: "#52606d"
  };

  function renderMarkers(visible) {
    markerLayer.clearLayers();
    markersById = {};
    var bounds = [];

    visible.forEach(function (item) {
      var beach = item.beach;
      if (beach.lat === null || beach.lng === null) return;

      var marker = L.circleMarker([beach.lat, beach.lng], {
        radius: 8,
        color: STATUS_COLORS[beach.dogs.status] || STATUS_COLORS.unknown,
        weight: 2,
        fillColor: STATUS_COLORS[beach.dogs.status] || STATUS_COLORS.unknown,
        fillOpacity: 0.5
      });

      var popup = document.createElement("div");
      var h2 = document.createElement("h2");
      h2.textContent = beach.name;
      popup.appendChild(h2);
      var district = document.createElement("p");
      district.textContent = beach.district;
      popup.appendChild(district);
      popup.appendChild(badgesFor(beach, item.restrictedHours));
      if (beach.dogs.notes) {
        var notes = document.createElement("p");
        notes.textContent = beach.dogs.notes;
        popup.appendChild(notes);
      }
      marker.bindPopup(popup);

      marker.addTo(markerLayer);
      markersById[beach.id] = marker;
      bounds.push([beach.lat, beach.lng]);
    });

    if (bounds.length) {
      map.fitBounds(bounds, { padding: [30, 30], maxZoom: 13 });
    }
  }

  /* ---------- init ---------- */

  function initMap() {
    map = L.map("map");
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors"
    }).addTo(map);
    markerLayer = L.layerGroup().addTo(map);
    map.setView([51.3, 1.1], 9); // Kent coast fallback before first fitBounds
  }

  function initControls() {
    var monthSelect = document.getElementById("month-filter");
    MONTH_NAMES.forEach(function (name, i) {
      var opt = document.createElement("option");
      opt.value = String(i + 1);
      opt.textContent = name;
      monthSelect.appendChild(opt);
    });
    monthSelect.value = String(state.month);

    document.getElementById("sandy-filter").addEventListener("change", function (ev) {
      state.sandy = ev.target.value;
      applyFilters();
    });
    document.getElementById("dog-filter").addEventListener("change", function (ev) {
      state.dog = ev.target.value;
      document.getElementById("month-group").hidden = state.dog !== "month";
      applyFilters();
    });
    monthSelect.addEventListener("change", function (ev) {
      state.month = parseInt(ev.target.value, 10);
      applyFilters();
    });
    document.getElementById("monitored-filter").addEventListener("change", function (ev) {
      state.monitored = ev.target.value;
      applyFilters();
    });
  }

  // Bound immediately (not in initControls) so the explainer works before data loads.
  (function () {
    var infoBtn = document.getElementById("monitored-info");
    var explainer = document.getElementById("monitored-explainer");
    infoBtn.addEventListener("click", function () {
      explainer.hidden = !explainer.hidden;
      infoBtn.setAttribute("aria-expanded", String(!explainer.hidden));
    });
  })();

  fetch("data/beaches.json")
    .then(function (resp) {
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      return resp.json();
    })
    .then(function (data) {
      beaches = data.beaches;
      document.getElementById("data-generated").textContent =
        "Dataset generated " + data.meta.generated + " · " + data.meta.beachCount + " beaches";
      initMap();
      initControls();
      applyFilters();
    })
    .catch(function (err) {
      var list = document.getElementById("beach-list");
      list.textContent = "Could not load beach data (" + err.message +
        "). Serve this directory over HTTP: python3 -m http.server";
    });
})();
