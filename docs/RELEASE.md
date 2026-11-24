# NovaOS 0.1.0 Alpha release runbook

## Trigger one Linux build

Create an empty GitHub repository you control and set its default branch to main. From the local NovaOS checkout, substitute the actual repository URL:

```powershell
git remote add origin https://github.com/OWNER/NovaOS.git
git push -u origin main
```

After authorizing the build's privileged container on GitHub's disposable runner, open **Actions → NovaOS ISO → Run workflow**, select **main**, and click **Run workflow**. With an authenticated GitHub CLI, the equivalent is:

```powershell
gh workflow run iso.yml --repo OWNER/NovaOS --ref main
gh run list --repo OWNER/NovaOS --workflow iso.yml --event workflow_dispatch --limit 1
gh run watch RUN_ID --repo OWNER/NovaOS --exit-status
```

Replace RUN_ID with the displayed database ID. Download the **novaos-build-log** artifact from any failed run. [GitHub manual workflow instructions](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)

## Download and verify the ISO

From the successful run's **Artifacts** section, download **novaos-amd64**. In PowerShell, in the download directory:

```powershell
Expand-Archive -LiteralPath .\novaos-amd64.zip -DestinationPath .\NovaOS-release
$iso = Get-ChildItem -LiteralPath .\NovaOS-release -Filter NovaOS-0.1.0-alpha-amd64.iso -File -Recurse
if (@($iso).Count -ne 1) { throw 'Expected exactly one release ISO' }
$entry = Select-String -LiteralPath (Join-Path $iso.DirectoryName SHA256SUMS) -Pattern '\sNovaOS-0\.1\.0-alpha-amd64\.iso$'
if (@($entry).Count -ne 1) { throw 'Expected exactly one checksum entry' }
$expected = ($entry.Line -split '\s+')[0]
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $iso.FullName).Hash -ne $expected) { throw 'ISO checksum mismatch' }
$iso.FullName
```

GitHub CLI can download and extract in one command. Use the checksum steps above after copying the download to the same destination:

```powershell
gh run download RUN_ID --repo OWNER/NovaOS -n novaos-amd64 -D .\NovaOS-release
```

The artifact includes BUILD-SUMMARY.md, KNOWN-ISSUES.md, LICENSE-NOTICES.md, the license archive and index, the installed package manifests, and SHA256SUMS. [GitHub artifact download instructions](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts)

## Boot and install separately

1. Use the verified ISO in a new diskless test VM. Set Linux/Debian 64-bit, 2 vCPUs, 4 GiB RAM, VMSVGA, 128 MiB video memory, NAT, and Intel HD Audio. Skip unattended installation, attach the ISO as optical media, and place Optical first. Boot **Start live desktop** and run the [VirtualBox checks](VIRTUALBOX.md). Start with BIOS, then repeat with EFI and Secure Boot disabled.
2. Create a second VM with a **new** virtual disk of at least 25 GiB. Attach the verified ISO and open **Install NovaOS** inside the live guest. Verify that cancelling the final confirmation leaves the disposable disk unchanged. On the actual install attempt, confirm only the intended virtual disk, then let Calamares finish.
3. Eject the ISO and boot from the virtual disk. Verify desktop login, Welcome, the requested apps, networking, audio, and signed updates. Record the firmware mode and whether encryption was selected. See [the guest benchmark procedure](../PERFORMANCE.md).

## Report bugs

Open an issue in the repository. Include the workflow run URL and commit, ISO SHA-256, VirtualBox version and firmware mode, VM CPU/RAM and graphics settings, exact reproduction steps, and the expected and observed result. For an installation failure include the Calamares log if available and mark whether the failure occurred before partition confirmation, during installation, or after ejecting the ISO. Remove personal information from logs before sharing. Use [BUGS.md](../BUGS.md) for severity and the current verification status.
