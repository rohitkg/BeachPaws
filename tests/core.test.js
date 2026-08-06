"use strict";

var test = require("node:test");
var assert = require("node:assert/strict");
var fs = require("node:fs");
var path = require("node:path");
var vm = require("node:vm");
var core = require("../core.js");

test("core module supports browser and Node loading", function () {
  var browser = {};
  browser.self = browser;
  var source = fs.readFileSync(path.join(__dirname, "..", "core.js"), "utf8");

  vm.runInNewContext(source, browser);

  assert.equal(typeof core.searchMatch, "function");
  assert.equal(typeof browser.BeachPawsCore.searchMatch, "function");
});

test("seasonal ban windows overlap only affected months", function () {
  var ban = { from: "05-01", to: "09-30" };

  assert.equal(core.monthOverlapsBan(4, ban), false);
  assert.equal(core.monthOverlapsBan(5, ban), true);
  assert.equal(core.monthOverlapsBan(9, ban), true);
  assert.equal(core.monthOverlapsBan(10, ban), false);
});

test("seasonal ban windows can wrap across the end of the year", function () {
  var ban = { from: "10-01", to: "03-31" };

  assert.equal(core.monthOverlapsBan(1, ban), true);
  assert.equal(core.monthOverlapsBan(3, ban), true);
  assert.equal(core.monthOverlapsBan(4, ban), false);
  assert.equal(core.monthOverlapsBan(9, ban), false);
  assert.equal(core.monthOverlapsBan(10, ban), true);
  assert.equal(core.monthOverlapsBan(12, ban), true);
});

test("dog matching distinguishes restricted hours from all-day bans", function () {
  var restrictedHours = {
    dogs: {
      status: "seasonal",
      ban: { from: "05-01", to: "09-30", daily: "10:00-18:00" },
    },
  };
  var allDay = {
    dogs: { status: "seasonal", ban: { from: "05-01", to: "09-30" } },
  };

  assert.equal(core.dogMatch(restrictedHours, "month", 7), "hours");
  assert.equal(core.dogMatch(allDay, "month", 7), "no");
  assert.equal(core.dogMatch(restrictedHours, "month", 11), "yes");
});

test("dog matching handles non-seasonal statuses", function () {
  var friendly = { dogs: { status: "friendly" } };
  var banned = { dogs: { status: "banned" } };
  var unknown = { dogs: { status: "unknown" } };

  assert.equal(core.dogMatch(friendly, "yearround", 7), "yes");
  assert.equal(core.dogMatch(banned, "banned", 7), "yes");
  assert.equal(core.dogMatch(unknown, "unknown", 7), "yes");
  assert.equal(core.dogMatch(unknown, "month", 7), "no");
});

test("normalization treats apostrophe variants alike", function () {
  assert.equal(core.normalize("St Margaret`s Bay"), "st margaret's bay");
  assert.equal(core.normalize("St Margaret’s Bay"), "st margaret's bay");
  assert.equal(core.normalize("St Margaret's Bay"), "st margaret's bay");
});

test("sand predicates cover single and mixed sediment combinations", function () {
  var sandOnly = { sandy: true, sediments: ["sand"] };
  var mixed = { sandy: true, sediments: ["sand", "shingle", "rock"] };
  var unknown = { sandy: false, sediments: [] };

  assert.equal(core.sandCategoryMatch(sandOnly, "sand-only"), true);
  assert.equal(core.sandCategoryMatch(sandOnly, "sand-shingle"), false);
  assert.equal(core.sandCategoryMatch(mixed, "sand-only"), false);
  assert.equal(core.sandCategoryMatch(mixed, "sand-shingle"), true);
  assert.equal(core.sandCategoryMatch(mixed, "sand-rock"), true);
  assert.equal(core.sandMatch(mixed, ["sand-only", "sand-rock"]), true);
  assert.equal(core.sandMatch(unknown, ["sand-only", "sand-rock"]), false);
  assert.equal(core.sandMatch(unknown, []), true);
});

test("search matches name, district, county and region", function () {
  var beach = {
    name: "St Margaret`s Bay",
    district: "Dover",
    county: "Kent",
    region: "South East",
  };

  assert.equal(core.searchMatch(beach, "margaret's"), true);
  assert.equal(core.searchMatch(beach, "DOVER"), true);
  assert.equal(core.searchMatch(beach, "kent"), true);
  assert.equal(core.searchMatch(beach, "south east"), true);
  assert.equal(core.searchMatch(beach, "cornwall"), false);
  assert.equal(core.searchMatch(beach, ""), true);
  assert.equal(core.searchMatch({ name: "Firestone Bay" }, "kent"), false);
});

test("beach location comparator sorts county, district, then name case-insensitively", function () {
  var beaches = [
    { id: "5", county: "Kent", district: "Dover", name: "samphire hoe" },
    { id: "3", county: "Cornwall", district: "Cornwall", name: "Porthcurno" },
    { id: "4", county: "Kent", district: "Thanet", name: "Botany Bay" },
    { id: "1", county: "kent", district: "dover", name: "Deal Castle" },
    { id: "2", county: "Kent", district: "Dover", name: "abbotts cliff" },
  ];

  beaches.sort(core.compareBeachLocation);

  assert.deepEqual(
    beaches.map(function (beach) {
      return beach.id;
    }),
    ["3", "2", "1", "5", "4"],
  );
});

test("beach location comparator sorts missing county or district after known values", function () {
  var beaches = [
    { id: "missing-county", district: "Dover", name: "No County" },
    { id: "known", county: "Kent", district: "Dover", name: "Known Beach" },
    { id: "missing-district", county: "Kent", name: "No District" },
    { id: "known-district", county: "Kent", district: "Canterbury", name: "Known District" },
  ];

  beaches.sort(core.compareBeachLocation);

  assert.deepEqual(
    beaches.map(function (beach) {
      return beach.id;
    }),
    ["known-district", "known", "missing-district", "missing-county"],
  );
});
