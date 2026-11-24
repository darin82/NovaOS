# VirtualBox live-boot test

Use a new **NovaOS Alpha Test** VM. If you already have a NovaOS VM with data, keep it separate. Only the downloaded ISO is required.

## Verify and attach the ISO

In PowerShell, from the extracted artifact directory, compare:

```powershell
Get-FileHash -Algorithm SHA256 .\NovaOS-0.1.0-alpha-amd64.iso
Get-Content .\SHA256SUMS
```

Create a VM with Type Linux and Version Debian (64-bit). Skip unattended installation and choose **Do Not Add a Virtual Hard Disk**. Set 2 vCPUs and 4 GB RAM. Under **Display**, start with **VMSVGA**, 128 MB video memory, and 3D acceleration disabled. Enable network adapter 1 with **NAT**. Enable audio output with the **Intel HD Audio** controller. Attach the verified ISO to a virtual optical drive and put Optical first in boot order.

Start with EFI disabled to test BIOS. Power off the test VM, enable EFI with Secure Boot disabled, and repeat from a cold boot. [Oracle VirtualBox manual](https://www.virtualbox.org/manual/)

## Acceptance checklist

- GRUB shows the NovaOS 0.1.0 Alpha menu. Select **Start live desktop**.
- In a fresh session open the quick settings icon beside the clock. Try mute, themes, and each effect independently. Apply Ultra Lite and verify the panel is opaque and `nova-appearance status` returns `false false false`. The Wi-Fi control requires a wireless interface and may be unavailable with VirtualBox NAT.
- With the guest keyboard captured, test Super, Super+E/I/L/D, Super+Arrow, Ctrl+Shift+Esc, and Super+Shift+S. If Windows intercepts a shortcut, repeat with VirtualBox's soft keyboard. Verify the screenshot action opens rectangular selection.
- Use Plasma Edit Mode to resize and align the panel, open the calendar and notification history from the tray, switch between two virtual desktops, and open the desktop context menu.
- The guest reaches the Plasma desktop without a login prompt. Check the Midnight Horizon wallpaper, branded launcher, centered panel, and Nova Midnight colors.
- Open Konsole and verify `echo "$XDG_SESSION_TYPE"` returns `wayland`. Check `grep -E '^(PRETTY_NAME|ID)=' /etc/os-release`.
- Open Firefox ESR and load an HTTPS page over NAT. Run `nmcli device status` and verify the Ethernet adapter is connected.
- Open Dolphin and browse the live home directory.
- Launch the ten Nova apps from Kickoff. In Nova Files test tabs, Places, previews, trash, archive extraction, and a test USB device if passthrough is available. In Nova Settings search for Display, Sound, Network, Bluetooth, Power, Accessibility and Autostart.
- In Nova Monitor check process controls and CPU, RAM, disks and network. Check GPU sensors on supported hardware. Right-click its launcher and open Startup Applications. In Nova Terminal check tabs and both Nova color schemes.
- In Nova Capture try region capture, copy to clipboard, and Wayland recording where available. In Nova Notes edit a named test file, wait for autosave, and check syntax highlighting. Open a sample movie with subtitles in Nova Media and try all three Nova Calculator modes.
- In Nova Update run the signed refresh and preview, then inspect an installed package. Review the APT prompt before applying changes. Repeat without networking to check the error path.
- Create a file with a distinctive name in the live home directory. From Dolphin, use Find to search by filename and confirm it appears. Check that `systemctl --user is-active kde-baloo.service` reports inactive.
- Run `wpctl status` and check for a playback sink. Use the speaker test in Plasma's Sound settings and confirm audio is audible on the host.
- Open System Settings → Colors, apply Nova Daybreak, then switch back to Nova Midnight.
- Run `flatpak --version`. To check signed Debian mirrors, run `sudo apt-get update` **inside the guest only**, with approval if required.
- Open Nova Performance and select each profile. For testing Gaming, run `nova-run --game -- sleep 30` in one terminal. In a second terminal, locate the active unit with `systemctl --user list-units 'nova-game-*.scope'` and check its `CPUWeight` using `systemctl --user show -p CPUWeight UNIT`. Confirm weight 800, and that `nova-run --maintenance -- true` exits 75 while the scope is active and succeeds after it exits.
- Open Nova Store and confirm LibreOffice is offered for install. With network available, install and remove it in the guest and confirm it is absent again.
- In Nova Store, verify category and source filters, screenshots where available, and a cancelled install that changes nothing. Check a per-user Flatpak's permissions and confirm package tools show real progress and errors.
- In Nova Music, import an authorized local audio file and play it. Check artwork and lyrics sidecars, playlist round trips, queue controls, the equalizer, tray, mini-player, media keys, and lock-screen playback controls. Stop playback and exit, then verify that Nova's mpv process stops. Test radio separately with guest networking enabled.
- For optional Nova AI, check that the clean image exposes no AI launcher. Enable it from Nova Store, test a local or approved cloud endpoint, stop a generation, review a system action, then close and disable the app. Confirm the managed Ollama instance has exited. See [Nova AI](AI.md).
- Record three cold boots from GRUB selection to a responsive desktop, along with VM settings and the release benchmark file.
- Check `swapon --show` for ZRAM, open and close the Performance Center, and confirm Eco → Ultra Lite → Balanced restores the previous look. Run `nova-benchmark --label optimized` from Konsole. See [the comparison procedure](../PERFORMANCE.md).
- Record BIOS and UEFI results, VirtualBox version, ISO SHA-256, and any issues in PROGRESS.md.

If the display stays black, collect `journalctl -b -u sddm`, `cat /var/log/live/config.log`, and `~/.local/share/sddm/wayland-session.log` when accessible from a guest TTY. The GRUB **Console diagnostics** entry boots to a login prompt. Sign in as `nova` with the Debian live-session password `live`. Try the alternate VMSVGA 3D setting in the test VM and report the setting used.

## Disposable install test

After the diskless test, create a separate VM with a new virtual disk of at least 25 GiB. Keep physical disks and the existing NovaOS VM detached. With the ISO mounted, open **Install NovaOS**. Test the profile, locale and encryption choices. Confirm the partition summary only after checking the virtual disk's identity and size. An install should never start when the confirmation is dismissed.

Eject the ISO after completion and boot the VM from its own virtual disk. Confirm local sign-in, one-time Nova Welcome, networking, audio, signed updates, and GRUB recovery entries. Repeat with another disposable virtual disk for encrypted install or a different firmware mode. Use [Nova Recovery](RECOVERY.md) only with the selected VM target.

## Polish and performance checks

Capture separate results at 1280×720, 1920×1080, 2560×1440 and 3840×2160 where supported. Test native and fractional scaling, keyboard focus, multiple displays, touchpad gestures, audio and network controls, a test USB device, suspend and wake, and a low-memory test VM. Check the SDDM login, lock screen, Plymouth splash, GRUB console diagnostics, and the encrypted unlock prompt. Compare a clean idle desktop against the same VM configuration using:

```sh
nova-benchmark --label optimized > optimized.json
```

After pushing main to the configured GitHub remote and authorizing the disposable build runner, start one Linux build with `gh workflow run iso.yml --ref main`. Use `gh run watch` and download the successful `novaos-amd64` artifact. Record its ISO checksum, workflow URL, and each VM result in PROGRESS.md.
