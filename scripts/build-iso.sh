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

for tool in lb debootstrap xorriso grub-script-check unsquashfs python3 sha256sum; do
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
BOOT="boot=live components live-config.nocomponents=sddm hostname=novaos username=$LIVE_USER quiet"
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
for app in nova-profile nova-run nova-store nova-appearance nova-update; do
    install -Dm0755 "$ROOT/apps/$app" "$tree/usr/bin/$app"
done
for input in launchers.tsv brand-launchers.awk; do
    install -Dm0644 "$ROOT/apps/$input" "$tree/usr/lib/novaos/$input"
done
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
    reports/performance-benchmark.json "$DEST/"
dpkg-query -W -f='${Package} \t${Version}\n' live-build debootstrap xorriso > "$DEST/build-tools.tsv"
cd "$DEST"
sha256sum "$ARTIFACT.iso" "$ARTIFACT.packages" build-tools.tsv \
    installed-packages.tsv background-services.tsv performance-benchmark.json > SHA256SUMS
printf 'Verified artifacts: %s\n' "$DEST"
