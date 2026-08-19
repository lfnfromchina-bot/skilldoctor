# Changelog

All notable changes to skilldoctor. This project follows semver-ish while in 0.x:
minor = new commands/features, patch = fixes and docs.

## [0.2.1] - 2026-08-17

- Hard-mode benchmark: 16 adversarial cases (keyword-free triggers, look-alike
  no_triggers) plus a deliberately greedy `universal-copywriter` competitor
- 14-model comparison matrix, incl. gpt-5 / gpt-5.1 / claude-opus-4-6 /
  gemini-2.5-pro / qwen3.7-max / deepseek-v4-pro; raw artifacts in `results/hard/`
- Docs: README first-screen badges; improve.png demo image

## [0.2.0] - 2026-08-17

- New command: `improve` — closed-loop description optimization
  (test → LLM rewrite → re-test against the full case set incl. no_trigger
  guardrails; `--write` applies the best candidate; `--json` as a CI gate)
- Demo run: naive xhs-writer 67% → 100% trigger rate in one round (gpt-4o-mini)

## [0.1.4] - 2026-08-17

- Fix: force UTF-8 stdio so redirected report output survives C/POSIX locales
  (UnicodeEncodeError mid-table when piping to a file on macOS)

## [0.1.3] - 2026-08-17

- Fix: reasoning models (deepseek-r1-style, kimi-k2.5) burned the whole
  `max_tokens=20` budget on hidden reasoning and emitted empty replies, scored
  as NONE. Default budget now 1024 with an automatic 4096 retry on truncation;
  new `--max-tokens` option
- Docs: 8-model comparison matrix in README

## [0.1.2] - 2026-08-15

- Three-line (academic) table style for reports
- Recursive skill discovery in collections

## [0.1.1] - 2026-08-15

- Renamed the CLI/package entry to `skilldoctor` (PyPI project: `skill-inspect`)

## [0.1.0] - 2026-08-15

- Initial release: `new` / `validate` / `lint` / `test`
