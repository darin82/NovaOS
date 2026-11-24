import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";

const source = readFileSync(new URL("../desktop/nova-layout.js", import.meta.url), "utf8");
const configured = new Map();
const desktop = { writeConfig: (key, value) => configured.set(key, value) };
const launcher = { writeConfig: desktop.writeConfig };
const tasks = { writeConfig: desktop.writeConfig };
const widgets = new Map([
    ["org.kde.plasma.kickoff", [launcher]],
    ["org.kde.plasma.icontasks", [tasks]],
    ["org.kde.plasma.digitalclock", [{ index: 4 }]],
]);
const bottom = {
    location: "bottom",
    widgets: id => widgets.get(id) ?? [],
    addWidget(id) {
        assert.equal(id, "org.novaos.quicksettings");
        const applet = {};
        widgets.set(id, [applet]);
        return applet;
    },
};
const top = { location: "top" };
for (let attempt = 0; attempt < 2; attempt++) {
    runInNewContext(source, { desktops: () => [desktop], panels: () => [bottom, top] });
}

assert.match(configured.get("Image"), /NovaOS\/contents\/images\/1920x1080.svg$/);
assert.equal(launcher.globalShortcut, "Alt+F1");
assert.equal(configured.get("icon"), "novaos");
assert.equal(configured.get("launchers").length, 3);
assert.equal(bottom.alignment, "center");
assert.equal(bottom.height, 48);
assert.equal(bottom.floating, true);
assert.equal(bottom.opacity, "translucent");
assert.equal(widgets.get("org.novaos.quicksettings")[0].index, 4);
assert.equal(top.height, undefined);
