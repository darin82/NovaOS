# NovaOS bug register

| Severity | Reproduction | Resolution |
| --- | --- | --- |
| High | Choose Minimal with media unchecked, boot the target and open Kickoff. The Music launcher could remain after the playback packages were removed. | Fixed in installer target cleanup. Source regression check passes. Guest retest pending. |
| High | Test an encrypted installation with the branded boot splash and wait for the unlock prompt. | Reused Plymouth's original two-step passphrase assets and callbacks. Encrypted boot remains unverified. |
| High | Build the image, open Calamares, cancel before confirmation, then install to a disposable disk and boot without the ISO. | Pending the first verified Linux build and VirtualBox install. |
| Medium | Open Store, Music, Gaming, AI and Performance at 720p and high display scaling. Check scrolling, focus, text wrapping and controls. | Shared card, spacing and feedback components added. Native rendering and scaling retests pending. |
| Medium | Sign in and lock, then restart. Check Nova branding, password entry, keyboard focus and power confirmation. | Greeter, lock wallpaper and splash assets wired into the ISO. Runtime verification pending. |
| Medium | Compare the same VM before and after polish using the benchmark in PERFORMANCE.md. | Pending real measurements. No performance regression conclusion yet. |
