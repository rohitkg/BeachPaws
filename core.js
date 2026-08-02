/* BeachPaws: pure filter predicates shared by the browser and Node tests. */
(function (root, factory) {
  "use strict";

  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.BeachPawsCore = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  function normalize(s) {
    return s.toLowerCase().replace(/[`’']/g, "'");
  }

  function pad2(n) {
    return (n < 10 ? "0" : "") + n;
  }

  // Zero-padded MM-DD strings preserve date order under lexical comparison.
  function monthOverlapsBan(month, ban) {
    var monthStart = pad2(month) + "-01";
    var monthEnd = pad2(month) + "-31";
    var windows =
      ban.from <= ban.to
        ? [[ban.from, ban.to]]
        : [
            [ban.from, "12-31"],
            ["01-01", ban.to],
          ];
    return windows.some(function (window_) {
      return !(monthEnd < window_[0] || monthStart > window_[1]);
    });
  }

  // Result: "yes" (include), "no" (exclude), "hours" (include with restricted hours).
  function dogMatch(beach, dogFilter, month) {
    var dogs = beach.dogs;
    switch (dogFilter) {
      case "any":
        return "yes";
      case "yearround":
        return dogs.status === "friendly" ? "yes" : "no";
      case "banned":
        return dogs.status === "banned" ? "yes" : "no";
      case "unknown":
        return dogs.status === "unknown" ? "yes" : "no";
      case "month":
        if (dogs.status === "friendly") return "yes";
        if (dogs.status === "seasonal") {
          if (!monthOverlapsBan(month, dogs.ban)) return "yes";
          return dogs.ban.daily ? "hours" : "no";
        }
        return "no";
    }
    return "yes";
  }

  function sandCategoryMatch(beach, category) {
    if (!beach.sandy) return false;
    switch (category) {
      case "sand-only":
        return beach.sediments.length === 1;
      case "sand-shingle":
        return beach.sediments.indexOf("shingle") !== -1;
      case "sand-rock":
        return beach.sediments.indexOf("rock") !== -1;
      case "sand-mud":
        return beach.sediments.indexOf("mud") !== -1;
    }
    return false;
  }

  // An empty selection means no filter. Otherwise any selected category can match.
  function sandMatch(beach, selected) {
    if (!selected.length) return true;
    return selected.some(function (category) {
      return sandCategoryMatch(beach, category);
    });
  }

  function searchMatch(beach, query) {
    if (!query) return true;
    var normalizedQuery = normalize(query);
    return !!(
      normalize(beach.name).indexOf(normalizedQuery) !== -1 ||
      (beach.district && normalize(beach.district).indexOf(normalizedQuery) !== -1) ||
      (beach.county && normalize(beach.county).indexOf(normalizedQuery) !== -1) ||
      (beach.region && normalize(beach.region).indexOf(normalizedQuery) !== -1)
    );
  }

  return {
    normalize: normalize,
    monthOverlapsBan: monthOverlapsBan,
    dogMatch: dogMatch,
    sandCategoryMatch: sandCategoryMatch,
    sandMatch: sandMatch,
    searchMatch: searchMatch,
  };
});
