# Valenced for iOS

An iOS-only fork of [Valenced](https://github.com/Valenced/valenced) for sideloading Discord 353.0 with Feather. Includes the native loader, shared plugin core, and JavaScript bundle; Android code has been removed.

- [Download the latest IPA](https://github.com/Sersium/valenceios/releases/tag/latest)
- **Feather source:** https://github.com/Sersium/valenceios/releases/download/latest/feather.json

Every push to `main` tests, builds, injects, and validates the app, then replaces the latest IPA and Feather feed. The exact supplied decrypted IPA is stored in the `base-ipa` release and checked against `ipa-source.json`. Feather supplies your signing certificate.

Targets ARM64 iPhones, including iPhone 17. Build checks cannot establish crash-free operation on a physical phone. Third-party JavaScript plugins require device testing; native-only plugins are disabled in release builds. Shake the phone to open recovery if a plugin causes problems.

**AI disclaimer:** This fork and its build pipeline were prepared with AI assistance. It is unofficial and is not endorsed by Discord or the upstream authors.

GPL-3.0; see [LICENSE](LICENSE).
