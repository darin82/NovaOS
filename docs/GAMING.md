# Nova Gaming Hub

Open **Nova Gaming Hub** from the application launcher. It loads local Steam manifests from standard native and Flatpak paths, including Steam library folders. The Hub reads installed size, recent activity, playtime and cached artwork where Steam exposes them. Manual games can be added and edited with an executable, an optional local image, and an argument list. You can use a client launcher as the executable for other libraries. Removing an entry leaves its files in place. The storage panel shows the install location and free space on its volume. Use Steam's Storage settings to move or uninstall Steam games.

## Setup and hardware

Gaming Setup reviews each install in Konsole. Flatpak apps are installed per user from Flathub after confirmation. Optional Debian utilities use signed APT and require the usual local authentication. GameMode, MangoHud, Gamescope, Wine, clients, OBS, and SDKs stay out of the base image. A candidate must be available in your configured repositories. Native Steam and 32-bit Wine may need Debian multiarch and additional signed archive components. Flatpak runtime extensions must match the application's runtime branch.

The graphics check reads PCI vendor IDs and bound drivers from DRM sysfs. AMD and Intel keep the Mesa Vulkan stack. Nova offers an NVIDIA driver install only after Debian's own detector recommends the corresponding package. Restricted archives and Secure Boot have their own setup requirements. In VirtualBox, accelerated gaming features depend on the virtual adapter.

## Play and compatibility

- For native Steam, paste the displayed Nova command into the game's **Properties → General → Launch Options**. Select a Proton version in **Properties → Compatibility**. The Hub links to ProtonDB reports for each Steam game. Valve's client owns the compatibility version selector.
- Flatpak Steam launches normally from the Hub. Configure Proton and any supported MangoHud or Gamescope extensions inside the Flatpak client. The host's Nova wrapper cannot manage the sandbox process directly.
- For legitimate Windows installers, add a Wine entry and select a local Wine executable. Nova launches it in a per-entry Wine prefix. Bottles manages its own runners and prefixes. A Wine entry can be updated to point at the installed program while retaining its prefix.
- Some titles use anti-cheat or DRM that the publisher has not enabled for Linux. Roblox has no supported native NovaOS path. Compatibility tools cannot guarantee games will work.

Managed launches select per-game scheduling settings without changing the global profile, optionally wrap a game with Gamescope or MangoHud, and restore effects on exit. GameMode applies in the Gaming profile when installed. Game scopes defer managed noncritical maintenance. MangoHud starts hidden and defaults to **Super+G** on supported configurations. Change the keysym string per game if the compositor or host intercepts the shortcut.

## Capture

Spectacle handles screenshots and supported Wayland recording. Install and open OBS for microphone and system audio capture, video quality selection, hardware encoders where available, and optional Replay Buffer. Set these up inside OBS and start capture or Replay Buffer only when requested. Nova does not enable automatic recording.

- [Valve Proton](https://github.com/ValveSoftware/Proton)
- [MangoHud configuration](https://github.com/flightlessmango/MangoHud)
- [Flathub OBS Studio](https://flathub.org/apps/com.obsproject.Studio)
