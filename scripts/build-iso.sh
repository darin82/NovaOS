#!/bin/sh
set -eu
umask 022

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
. "$ROOT/build/settings.env"
VERSION=$(cat "$ROOT/VERSION")
IMAGE="novaos-$VERSION-alpha"
ARTIFACT="$IMAGE-$ARCH"
PHASE=preflight

on_exit() {
    status=$?
    if [ "$status" -ne 0 ]; then
        printf 'NovaOS build failed during %s (exit %s).\n' "$PHASE" "$status" >&2
    fi
}
trap on_exit EXIT

if [ "$(uname -s)" != Linux ] || [ "$(uname -m)" != x86_64 ] || [ "$(id -u)" -ne 0 ]; then
    echo 'Build requires root on an x86-64 Linux build worker.' >&2
    exit 1
fi

if [ ! -r /etc/debian_version ] || ! grep -Eq '^13([.]|$)' /etc/debian_version; then
    echo 'Use the Debian 13 build environment in build/container.Dockerfile.' >&2
    exit 1
fi

for tool in lb debootstrap xorriso grub-script-check unsquashfs python3 sha256sum rsvg-convert; do
    command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 1; }
done
python3 "$ROOT/tests/validate-source.py"
if [ -n "${GITHUB_REF_NAME:-}" ] && [ "${GITHUB_REF_TYPE:-}" = tag ] &&
    [ "$GITHUB_REF_NAME" != "v$VERSION-alpha" ]; then
    echo "Expected release tag v$VERSION-alpha; got $GITHUB_REF_NAME." >&2
    exit 1
fi

# A fresh workspace prevents live-build caches or mounts from affecting retries.
BUILD_DIR=$(mktemp -d "${TMPDIR:-/tmp}/novaos.XXXXXXXX")
printf 'Build directory: %s\n' "$BUILD_DIR"
cd "$BUILD_DIR"

PHASE=configuration
BOOT="boot=live components live-config.nocomponents=sddm hostname=novaos username=$LIVE_USER quiet splash"
lb config noauto \
    --mode debian --distribution "$SUITE" --architectures "$ARCH" \
    --debootstrap-options '--include=ca-certificates' \
    --archive-areas "$ARCHIVE_AREAS" --apt-secure true --apt-recommends false \
    --mirror-bootstrap "$MIRROR" --mirror-chroot "$MIRROR" \
    --mirror-binary "$MIRROR" --mirror-chroot-security "$SECURITY_MIRROR" \
    --mirror-binary-security "$SECURITY_MIRROR" --security true --updates true \
    --binary-images iso-hybrid --bootloaders 'grub-pc grub-efi' \
    --uefi-secure-boot disable --debian-installer none --memtest none \
    --firmware-chroot false --firmware-binary false --linux-flavours amd64 \
    --bootappend-live "$BOOT" --bootappend-live-failsafe none \
    --checksums sha256 --image-name "$IMAGE" --iso-volume "NovaOS $VERSION Alpha" \
    --iso-application "NovaOS $VERSION Alpha" --iso-publisher 'NovaOS Project'

cp -R "$ROOT/config/." config/
cp "$ROOT/packages/"*.list.chroot config/package-lists/
sed "s/@NOVA_VERSION@/$VERSION/g" "$ROOT/config/bootloaders/grub-pc/grub.cfg.in" \
    > config/bootloaders/grub-pc/grub.cfg
rm config/bootloaders/grub-pc/grub.cfg.in

tree=config/includes.chroot
wallpaper="$tree/usr/share/wallpapers/NovaOS"
install -Dm0644 "$ROOT/branding/novaos.svg" "$tree/usr/share/icons/hicolor/scalable/apps/novaos.svg"
install -Dm0644 "$ROOT/branding/novaos.svg" "$tree/usr/share/desktop-base/nova-logo.svg"
install -Dm0644 "$ROOT/branding/wallpaper.svg" "$wallpaper/contents/images/1920x1080.svg"
install -Dm0644 "$ROOT/branding/wallpaper.json" "$wallpaper/metadata.json"
for scheme in "$ROOT/desktop/"*.colors; do
    install -Dm0644 "$scheme" "$tree/usr/share/color-schemes/$(basename "$scheme")"
done
install -Dm0644 "$ROOT/desktop/kdeglobals" "$tree/etc/xdg/kdeglobals"
install -Dm0644 "$ROOT/desktop/kwinrc" "$tree/etc/xdg/kwinrc"
install -Dm0644 "$ROOT/desktop/kscreenlockerrc" "$tree/etc/xdg/kscreenlockerrc"
greeter="$tree/usr/share/sddm/themes/novaos"
install -Dm0644 "$ROOT/desktop/sddm/metadata.desktop" "$greeter/metadata.desktop"
install -Dm0644 "$ROOT/desktop/sddm/Main.qml" "$greeter/Main.qml"
install -Dm0644 "$ROOT/branding/novaos.svg" "$greeter/novaos.svg"
install -Dm0644 "$ROOT/branding/wallpaper.svg" "$greeter/wallpaper.svg"
install -Dm0644 "$ROOT/desktop/sddm/50-novaos.conf" "$tree/etc/sddm.conf.d/50-novaos.conf"
boot_theme="$tree/usr/share/plymouth/themes/novaos"
install -Dm0644 "$ROOT/desktop/plymouth/novaos.plymouth" "$boot_theme/novaos.plymouth"
rsvg-convert --width 96 --height 96 "$ROOT/branding/novaos.svg" > "$boot_theme/watermark.png"
# KGlobalAccel uses KConfig::SimpleConfig and only reads its user copy.
install -Dm0644 "$ROOT/desktop/kglobalshortcutsrc" "$tree/etc/skel/.config/kglobalshortcutsrc"
applet="$tree/usr/share/plasma/plasmoids/org.novaos.quicksettings"
install -Dm0644 "$ROOT/desktop/quick-settings/metadata.json" "$applet/metadata.json"
install -Dm0644 "$ROOT/desktop/quick-settings/contents/ui/main.qml" "$applet/contents/ui/main.qml"
for theme in NovaMidnight NovaDaybreak; do
    inherits=breeze
    if [ "$theme" = NovaMidnight ]; then
        inherits=breeze-dark
    fi
    icons="$tree/usr/share/icons/$theme"
    install -Dm0644 "$ROOT/desktop/icons/quick-settings.svg" "$icons/scalable/actions/nova-quick-settings.svg"
    for icon in "$ROOT/desktop/icons/"nova-*.svg; do
        install -Dm0644 "$icon" "$icons/scalable/actions/$(basename "$icon")"
    done
    cat > "$icons/index.theme" <<EOF
[Icon Theme]
Name=$theme
Inherits=$inherits,hicolor
Directories=scalable/actions

[scalable/actions]
Size=24
MinSize=16
MaxSize=96
Type=Scalable
Context=Actions
EOF
done
# KConfig reads the palette groups from the system kdeglobals on the first login.
sed -n '/^\[Colors:/,$p' "$ROOT/desktop/NovaMidnight.colors" >> "$tree/etc/xdg/kdeglobals"
install -Dm0644 "$ROOT/desktop/nova-layout.js" \
    "$tree/usr/share/plasma/shells/org.kde.plasma.desktop/contents/updates/10-nova-layout.js"
install -Dm0644 "$ROOT/apps/mimeapps.list" "$tree/etc/xdg/mimeapps.list"
install -Dm0644 "$ROOT/desktop/baloofilerc" "$tree/etc/xdg/baloofilerc"
install -d -m 0755 "$tree/etc/systemd/user"
ln -s /dev/null "$tree/etc/systemd/user/kde-baloo.service"
for rc in dolphinrc katerc harunarc konsolerc; do
    install -Dm0644 "$ROOT/desktop/$rc" "$tree/etc/xdg/$rc"
done
for profile in "$ROOT/desktop/konsole/"*; do
    install -Dm0644 "$profile" "$tree/usr/share/konsole/$(basename "$profile")"
done
for app in nova-profile nova-run nova-appearance nova-update nova-music; do
    install -Dm0755 "$ROOT/apps/$app" "$tree/usr/bin/$app"
done
for input in launchers.tsv brand-launchers.awk; do
    install -Dm0644 "$ROOT/apps/$input" "$tree/usr/lib/novaos/$input"
done
install -Dm0644 "$ROOT/apps/Performance.qml" "$tree/usr/lib/novaos/Performance.qml"
install -Dm0644 "$ROOT/apps/Gaming.qml" "$tree/usr/lib/novaos/Gaming.qml"
for qml in NovaBridge NovaStyle NovaNotice NovaLoading NovaCard Music Store; do
    install -Dm0644 "$ROOT/apps/$qml.qml" "$tree/usr/lib/novaos/$qml.qml"
done
for file in AI.qml org.novaos.AI.desktop actions.py providers.py ollama_install.py; do
    install -Dm0644 "$ROOT/apps/ai/$file" "$tree/usr/lib/novaos/ai/$file"
done
for file in nova-ai nova-ai.py; do
    install -Dm0755 "$ROOT/apps/ai/$file" "$tree/usr/lib/novaos/ai/$file"
done
install -Dm0755 "$ROOT/apps/nova-music.py" "$tree/usr/lib/novaos/nova-music.py"
install -Dm0755 "$ROOT/apps/nova-store.py" "$tree/usr/bin/nova-store"
install -Dm0644 "$ROOT/apps/store-catalog.json" "$tree/usr/share/novaos/store-catalog.json"
install -Dm0644 "$ROOT/apps/mangohud.conf" "$tree/usr/share/novaos/mangohud.conf"
install -Dm0755 "$ROOT/apps/nova-gaming.py" "$tree/usr/bin/nova-gaming"
install -Dm0755 "$ROOT/apps/nova-metrics.py" "$tree/usr/lib/novaos/nova-metrics.py"
install -Dm0755 "$ROOT/scripts/benchmark-guest.py" "$tree/usr/bin/nova-benchmark"

installer="$ROOT/installer"
calamares="$tree/etc/calamares"
install -Dm0644 "$installer/settings.conf" "$calamares/settings.conf"
for module in "$installer/modules/"*.conf; do
    install -Dm0644 "$module" "$calamares/modules/$(basename "$module")"
done
for module in nova-prepare nova-install; do
    for file in main.py module.desc; do
        install -Dm0644 "$installer/modules/$module/$file" "$tree/usr/lib/calamares/modules/$module/$file"
    done
done
brand="$calamares/branding/novaos"
install -Dm0644 "$installer/branding/novaos/show.qml" "$brand/show.qml"
sed "s/@VERSION@/$VERSION/g" "$installer/branding/novaos/branding.desc.in" > "$brand/branding.desc"
install -Dm0644 "$ROOT/branding/novaos.svg" "$brand/novaos.svg"
install -Dm0644 "$ROOT/branding/wallpaper.svg" "$brand/wallpaper.svg"
for name in nova-install nova-recovery nova-welcome nova-update-notify; do
    install -Dm0755 "$installer/$name" "$tree/usr/bin/$name"
done
install -Dm0644 "$installer/org.novaos.Install.desktop" "$tree/usr/share/applications/org.novaos.Install.desktop"
install -Dm0644 "$installer/org.novaos.Install.desktop" "$tree/usr/share/novaos/desktop/Install NovaOS.desktop"
install -Dm0644 "$installer/org.novaos.Recovery.desktop" "$tree/usr/share/applications/org.novaos.Recovery.desktop"
install -Dm0644 "$installer/calamares-upstream-hidden.desktop" "$tree/etc/xdg/autostart/calamares-desktop-icon.desktop"
install -Dm0644 "$installer/calamares-upstream-hidden.desktop" "$tree/usr/local/share/applications/calamares-install-debian.desktop"
install -Dm0644 "$installer/live-setup.desktop" "$tree/etc/xdg/autostart/nova-live-installer.desktop"
install -Dm0644 "$installer/nova-welcome.desktop" "$tree/etc/xdg/autostart/nova-welcome.desktop"
install -Dm0644 "$installer/Welcome.qml" "$tree/usr/lib/novaos/Welcome.qml"
install -Dm0755 "$installer/nova-welcome-action.py" "$tree/usr/lib/novaos/nova-welcome-action.py"
for unit in service timer; do
    install -Dm0644 "$installer/nova-update-notify.$unit" "$tree/usr/lib/systemd/user/nova-update-notify.$unit"
done
install -Dm0644 "$ROOT/docs/RECOVERY.md" "$tree/usr/share/doc/novaos/recovery/RECOVERY.md"
for entry in "$ROOT/apps/"*.desktop; do
    install -Dm0644 "$entry" "$tree/usr/share/applications/$(basename "$entry")"
done
install -d -m0755 "$tree/usr/lib/novaos"
cat > "$tree/usr/lib/novaos/os-release" <<EOF
NAME="NovaOS"
PRETTY_NAME="NovaOS $VERSION Alpha"
ID=novaos
ID_LIKE=debian
VERSION_ID="$VERSION"
VERSION="$VERSION Alpha"
VERSION_CODENAME=trixie
DEBIAN_CODENAME=trixie
LOGO=novaos
EOF
chmod 0755 config/hooks/live/*.hook.chroot "$tree/usr/lib/live/config/0086-nova-sddm"

PHASE=live-build
lb build

PHASE='ISO verification'
mkdir reports
sh "$ROOT/tests/verify-iso.sh" "$ARTIFACT.hybrid.iso" "$ARTIFACT.packages" "$VERSION" "$BUILD_DIR/reports"

PHASE='artifact collection'
DEST="$ROOT/dist/$ARTIFACT"
if [ -e "$DEST" ]; then
    echo "Artifacts already exist at $DEST; use a fresh checkout for another build." >&2
    exit 1
fi
mkdir -p "$DEST"
install -m0644 "$ARTIFACT.hybrid.iso" "$DEST/$ARTIFACT.iso"
install -m0644 "$ARTIFACT.packages" "$DEST/$ARTIFACT.packages"
install -m0644 reports/installed-packages.tsv reports/background-services.tsv \
    reports/package-sizes.tsv reports/performance-benchmark.json "$DEST/"
dpkg-query -W -f='${Package} \t${Version}\n' live-build debootstrap xorriso > "$DEST/build-tools.tsv"
cd "$DEST"
sha256sum "$ARTIFACT.iso" "$ARTIFACT.packages" build-tools.tsv \
    installed-packages.tsv background-services.tsv package-sizes.tsv performance-benchmark.json > SHA256SUMS
printf 'Verified artifacts: %s\n' "$DEST"
