#!/bin/sh
set -eu
export LC_ALL=C
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ISO=$(realpath "$1")
MANIFEST=$(realpath "$2")
VERSION=$3
REPORTS=$4
WORK=$(mktemp -d)
trap 'rm -rf -- "$WORK"' EXIT

test -s "$ISO"
test -s "$MANIFEST"
xorriso -indev "$ISO" -report_el_torito plain > "$WORK/boot-report"
grep -Eq 'El Torito boot img.* BIOS ' "$WORK/boot-report"
grep -Eq 'El Torito boot img.* UEFI ' "$WORK/boot-report"

xorriso -osirrox on -indev "$ISO" \
    -extract /boot/grub/grub.cfg "$WORK/grub.cfg" \
    -extract /live/filesystem.squashfs "$WORK/filesystem.squashfs" \
    -extract /live/filesystem.packages "$WORK/filesystem.packages"
cmp "$MANIFEST" "$WORK/filesystem.packages"
grub-script-check "$WORK/grub.cfg"
if grep -Eq '@[A-Z_]+@' "$WORK/grub.cfg"; then
    echo 'Unexpanded GRUB template token' >&2
    exit 1
fi
grep -Fq "NovaOS $VERSION Alpha - Start live desktop" "$WORK/grub.cfg"
awk '$1=="linux" || $1=="initrd" {print $2}' "$WORK/grub.cfg" | sort -u > "$WORK/boot-paths"
test -s "$WORK/boot-paths"
while IFS= read -r path; do
    case "$path" in
        /live/*) ;;
        *) echo "Unexpected boot path: $path" >&2; exit 1 ;;
    esac
    xorriso -osirrox on -indev "$ISO" -extract "$path" "$WORK/boot-file"
    test -s "$WORK/boot-file"
    rm "$WORK/boot-file"
done < "$WORK/boot-paths"

# Compare all explicitly requested packages to the resolved image manifest.
awk 'NF {sub(/:.*/, "", $1); print $1}' "$MANIFEST" | sort -u > "$WORK/installed"
for list in "$ROOT/packages/"*.list.chroot; do
    while IFS= read -r package; do
        if ! grep -Fxq "$package" "$WORK/installed"; then
            echo "Package missing from image: $package" >&2
            exit 1
        fi
    done < "$list"
done

unsquashfs -cat "$WORK/filesystem.squashfs" etc/os-release > "$WORK/os-release"
grep -Fxq "VERSION_ID=\"$VERSION\"" "$WORK/os-release"
grep -Fxq 'ID=novaos' "$WORK/os-release"
unsquashfs -cat "$WORK/filesystem.squashfs" etc/apt/sources.list > "$WORK/sources.list"
grep -Eq '^deb .* trixie-security ' "$WORK/sources.list"
for asset in \
    usr/share/wallpapers/NovaOS/contents/images/1920x1080.svg \
    usr/share/icons/hicolor/scalable/apps/novaos.svg \
    usr/share/color-schemes/NovaMidnight.colors \
    usr/share/color-schemes/NovaDaybreak.colors \
    usr/share/plasma/shells/org.kde.plasma.desktop/contents/updates/10-nova-layout.js \
    usr/share/plasma/plasmoids/org.novaos.quicksettings/metadata.json \
    usr/share/plasma/plasmoids/org.novaos.quicksettings/contents/ui/main.qml \
    usr/share/icons/NovaMidnight/scalable/actions/nova-quick-settings.svg \
    usr/share/icons/NovaDaybreak/scalable/actions/nova-quick-settings.svg \
    etc/skel/.config/kglobalshortcutsrc \
    etc/xdg/kwinrc \
    usr/bin/nova-appearance \
    usr/share/wayland-sessions/plasma.desktop
do
    unsquashfs -cat "$WORK/filesystem.squashfs" "$asset" > "$WORK/guest-file"
    test -s "$WORK/guest-file"
done
for report in installed-packages.tsv background-services.tsv; do
    unsquashfs -cat "$WORK/filesystem.squashfs" "usr/lib/novaos/reports/$report" > "$REPORTS/$report"
done
cp "$MANIFEST" "$REPORTS/live.packages"
python3 "$ROOT/scripts/audit-image.py" "$ROOT" "$REPORTS"
python3 "$ROOT/scripts/benchmark-release.py" "$ISO" "$WORK/filesystem.squashfs" "$REPORTS/performance-benchmark.json"
printf 'ISO structure, boot entries, APT security source and package inventory verified.\n'
