# Resume Workshop · Local Resume Studio

> A local-first AI workspace that turns an existing resume into a reusable profile, then generates, edits, lays out, and exports a resume tailored to a target job description.

[中文说明](README.md) · [Privacy](PRIVACY.md) · [Security](SECURITY.md) · [License](LICENSE.en.md)

## Highlights

- Import DOCX, PDF, scanned resumes, or multiple images and confirm parsed facts before saving.
- Paste a job description or extract it from screenshots with an auditable OCR correction flow.
- Generate separate same-career and career-switch resume drafts without overwriting the base profile.
- Edit modules manually, ask AI to change a selected field or the full draft, and undo/redo changes.
- Turn a local project folder into an evidence-backed project-case draft.
- Build career-switch learning paths and optionally find specific free course resources.
- Import Word/PDF/image templates, preview the final layout, and export editable Word or stable PDF files.
- Keep multiple job variants, snapshots, and local backups that exclude API keys.

The UI is currently Chinese because the primary audience is domestic Chinese job seekers.

## AI providers

Supported configurations include DeepSeek, OpenAI, Anthropic Claude, MiniMax, GLM, Kimi, MiMo, Ollama, LM Studio, and a custom OpenAI-compatible endpoint. DeepSeek is the default cloud provider; Ollama and LM Studio enable local inference.

Users supply their own keys. Keys are stored locally per provider and are excluded from backups, repository files, and resume content. Providers for which the maintainer has no live key are validated with protocol-level mocked tests; use the in-app connection test to verify your own account, model, and regional endpoint.

## Run from source

Python 3.12 is recommended:

```powershell
python -m pip install -r requirements.txt
python -m app.main
```

Open `http://127.0.0.1:8877`. Windows users can also run `start.bat`.

Packaged Windows and macOS builds are published on [GitHub Releases](https://github.com/wu-hongliii/resume-workshop/releases). Builds are currently unsigned, so operating systems may show an unknown-publisher warning. Download only from this repository and verify the published SHA-256 checksum.

## Privacy and responsible use

Profiles, job variants, and history stay on the local computer by default. Data is sent to a cloud AI, OCR-text correction service, or course-search service only after an explicit user action. The project contains no telemetry or automatic crash reporting. See [PRIVACY.md](PRIVACY.md).

AI and OCR output can be wrong. Review every claim before submitting a resume. Do not fabricate verifiable employment, education, certificates, identities, or exact performance figures.

## License

This project is **source-available**, not OSI open source. Personal, educational, job-seeking, and free internal organizational use are allowed. Unauthorized paid resale, paid packaging, paid resume/training/recruiting services, and paid hosted services are prohibited. Free modified distributions must be renamed, marked unofficial, attributed, and accompanied by complete source under the same terms.

The complete Chinese [LICENSE](LICENSE) controls. For commercial licensing, contact `2725275630@qq.com`.

## Contributing

Use Issues for ordinary bug reports and feature requests. Read [CONTRIBUTING.md](CONTRIBUTING.md) and [CLA.md](CLA.md) before opening a pull request. Report vulnerabilities privately according to [SECURITY.md](SECURITY.md).

Voluntary support is available in the in-app About page. It never unlocks features or changes support eligibility.
