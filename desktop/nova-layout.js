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
        launcher.currentConfigGroup = ["General"];
        launcher.writeConfig("icon", "novaos");
    }
}
