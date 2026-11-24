// Apply once per Plasma profile after the stock panel and desktops exist.
const wallpaper = "file:///usr/share/wallpapers/NovaOS/contents/images/1920x1080.svg";

for (const desktop of desktops()) {
    desktop.wallpaperPlugin = "org.kde.image";
    desktop.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
    desktop.writeConfig("Image", wallpaper);
}

for (const panel of panels()) {
    if (panel.location !== "bottom") {
        continue;
    }

    panel.height = 48;
    panel.alignment = "center";
    panel.lengthMode = "fit";
    panel.floating = true;
    panel.opacity = "translucent";
    const launcher = panel.widgets("org.kde.plasma.kickoff")[0];
    if (launcher) {
        if (!launcher.globalShortcut) {
            launcher.globalShortcut = "Alt+F1";
        }
        launcher.currentConfigGroup = ["General"];
        launcher.writeConfig("icon", "novaos");
    }

    const quickSettingsId = "org.novaos.quicksettings";
    if (panel.widgets(quickSettingsId).length === 0) {
        const quickSettings = panel.addWidget(quickSettingsId);
        const clock = panel.widgets("org.kde.plasma.digitalclock")[0];
        if (quickSettings && clock) {
            quickSettings.index = clock.index;
        }
    }

    for (const tasks of panel.widgets("org.kde.plasma.icontasks")) {
        tasks.currentConfigGroup = ["General"];
        tasks.writeConfig("launchers", [
            "applications:firefox-esr.desktop",
            "applications:org.kde.dolphin.desktop",
            "applications:org.kde.konsole.desktop"
        ]);
    }
}
