# Contributing to skilldoctor

Thanks for considering a contribution! This project is small on purpose —
the best contributions right now are:

- **Benchmark cases**: new domains, adversarial no_triggers, multilingual
  phrasings (see `examples/xhs-writer/skilldoctor.cases-hard.yml` for the style)
- **Bug reports**: especially "the simulated router did X but real agent Y did Z"
- **Docs**: clearer wording, more examples, translations
- **Code**: open an issue first for anything bigger than a typo fix

## Setup

```bash
git clone https://github.com/lfnfromchina-bot/skilldoctor && cd skilldoctor
pip install -e '.[dev]'
pytest
```

Tests must pass and new behavior needs new tests. LLM-touching code paths
should be unit-tested with a mocked OpenAI client — see
`tests/test_tester.py` and `tests/test_improver.py` for the pattern
(never hit a real API in tests).

## Conventions

- Pure logic in `parser.py` / `validator.py` / `linter.py` — importable as a library
- LLM calls only in `tester.py` / `improver.py` / `router_prompt.py`
- Rich output in `report.py` only; keep reports CJK-safe (CLI forces UTF-8 stdio)
- CLI prompts are English-first; Chinese via locale detection or `--lang zh`

## Releasing (maintainer)

Bump `version` in `pyproject.toml` **and** `__version__` in
`src/skilldoctor/__init__.py`, tag `vX.Y.Z`, push the tag — Trusted
Publishing ships it to PyPI.
