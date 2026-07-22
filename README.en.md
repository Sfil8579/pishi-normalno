<div align="center">
  <img src="assets/hero.png" alt="Pishi Normalno. Russian editor for AI agents" width="100%">
</div>

# Pishi Normalno

`pishi-normalno` is a Russian-first writing and editing skill for AI agents. It preserves facts, semantic relations, uncertainty, and author voice while removing synthetic phrasing, bureaucratic language, calques, broken sentence fragments, decorative Unicode, and formulaic marketing copy.

**[Download the ready-to-upload skill ZIP](https://github.com/fsbtactic-code/pishi-normalno/releases/download/v1.0.0/pishi-normalno.zip)**

It does not add mistakes, slang, metaphors, or random sentence variation to imitate a person. It does not promise to bypass AI detectors. Its target is strong Russian prose.

## The difference in one example

Broken edit:

> Аккуратный промпт. Трата твоего времени.

Meaning-preserving edit:

> Аккуратный промпт отнимает у тебя время.

The skill restores the missing predication instead of replacing punctuation mechanically.

## Highlights

- Write, edit, sharpen, rewrite, audit, and embedded modes.
- Source-aware checks for numbers, URLs, quotes, modality, causality, benefits, address register, and sentence relation splits.
- Dedicated marketing, SMM, Telegram, Threads, landing page, case study, CTA, and product-copy guidance.
- Automatic invocation metadata for compatible clients.
- Deterministic local CLI with JSON output and no telemetry.
- 33 composite editorial patterns, 21 machine-readable rule groups, and 80 automated tests at the initial release.

## Install

The complete guide covers Claude, Claude Desktop, Claude Code, ChatGPT, and Codex: [INSTALL.md](INSTALL.md).

Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/fsbtactic-code/pishi-normalno/v1.0.0/install.ps1 | iex
```

macOS and Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/fsbtactic-code/pishi-normalno/v1.0.0/install.sh | bash
```

From a clone:

```bash
git clone https://github.com/fsbtactic-code/pishi-normalno.git
cd pishi-normalno
python -m pip install .
pishi-normalno install --target codex
```

## CLI

```bash
pishi-normalno audit result.md --source source.md --genre social --strict
pishi-normalno doctor
```

## Acknowledgement and comparison

We studied and used approaches from [`ilyautov/humanizer-ru`](https://github.com/ilyautov/humanizer-ru), including its modular design, multi-pass review, Russian pattern catalog, false-positive awareness, optional morphology, and evaluation culture. `humanizer-ru` is MIT-licensed by Ilya Utov. This project is not affiliated with or endorsed by Ilya Utov. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

The projects make different choices. `humanizer-ru` includes detector-oriented perplexity and burstiness goals. `pishi-normalno` instead prioritizes semantic fidelity, source-aware comparison, writing from scratch, marketing claim provenance, and minimal intervention. The Russian README contains the full comparison.

## License

MIT. No text is sent to external services by the CLI.
