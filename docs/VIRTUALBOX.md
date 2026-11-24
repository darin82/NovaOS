# VirtualBox live-boot test

Use a new **NovaOS Alpha Test** VM. If you already have a NovaOS VM with data, keep it separate. Only the downloaded ISO is required.

## Verify and attach the ISO

In PowerShell, from the extracted artifact directory, compare:

```powershell
Get-FileHash -Algorithm SHA256 .\novaos-0.1.0-alpha-amd64.iso
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
- Create a file with a distinctive name in the live home directory. From Dolphin, use Find to search by filename and confirm it appears. Check that `systemctl --user is-active kde-baloo.service` reports inactive.
- Run `wpctl status` and check for a playback sink. Use the speaker test in Plasma's Sound settings and confirm audio is audible on the host.
- Open System Settings → Colors, apply Nova Daybreak, then switch back to Nova Midnight.
- Run `flatpak --version`. To check signed Debian mirrors, run `sudo apt-get update` **inside the guest only**, with approval if required.
- Open Nova Performance and select each profile. For testing Gaming, run `nova-run --game -- sleep 30` in one terminal. In a second terminal, locate the active unit with `systemctl --user list-units 'nova-game-*.scope'` and check its `CPUWeight` using `systemctl --user show -p CPUWeight UNIT`. Confirm weight 800, and that `nova-run --maintenance -- true` exits 75 while the scope is active and succeeds after it exits.
- Open Nova Store and confirm LibreOffice is offered for install. With network available, install and remove it in the guest and confirm it is absent again.
- Record three cold boots from GRUB selection to a responsive desktop, along with VM settings and the release benchmark file.
- Record BIOS and UEFI results, VirtualBox version, ISO SHA-256, and any issues in PROGRESS.md.

If the display stays black, collect `journalctl -b -u sddm`, `cat /var/log/live/config.log`, and `~/.local/share/sddm/wayland-session.log` when accessible from a guest TTY. The GRUB **Console diagnostics** entry boots to a login prompt. Sign in as `nova` with the Debian live-session password `live`. Try the alternate VMSVGA 3D setting in the test VM and report the setting used.
