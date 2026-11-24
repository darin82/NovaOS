# Nova Recovery

Boot the NovaOS ISO and select **Recovery desktop**. Nova Recovery's menu inspects hardware, exports logs, and copies user-selected backups or restores to new paths. It asks for privileged authorization only for SMART reads. It never formats storage.

Only use the following examples after identifying the target in `lsblk`. The placeholders must be replaced with the disposable VM's devices and mount locations. Match the installed system's firmware mode.

## Bootloader and package repair

Mount the installed root under `/mnt/nova`. For encrypted installations unlock the selected volume first. Also mount a separate `/boot` if present and mount the EFI partition at `/mnt/nova/boot/efi` in UEFI mode. Bind-mount /dev, /proc, and /sys into the target before repair.

```sh
sudo nova-recovery boot /mnt/nova /dev/SELECTED_DISK
sudo nova-recovery packages /mnt/nova
```

Review the target and type the required confirmation phrase. Boot repair writes GRUB and may update UEFI boot entries. Package repair resumes dpkg and uses signed Debian sources. Run `nova-recovery desktop` from a text console after logging out of Plasma to move desktop settings to a backup.

## Btrfs system snapshots

On supported layouts, mount the Btrfs top level with `subvolid=5` beneath `/mnt`. The tools require an installed `@` root and separate `@home` subvolume. Create a read-only system snapshot with `sudo nova-recovery snapshot-create /mnt/nova-top NAME`. From the live ISO with `@` unmounted, use `sudo nova-recovery snapshot-restore /mnt/nova-top NAME`. Restore preserves the previous system under a timestamped name. This workflow does not roll back a separate EFI or boot partition. Check boot and kernel consistency afterward.

System snapshots retain system files on the same disk. For personal files, copy selected files to a different volume using `nova-recovery files SOURCE NEW_DESTINATION`. The tool refuses overwrites. Other filesystem layouts can use file backups and the boot/package repair commands.
