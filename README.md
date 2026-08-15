# skillvet

**Scaffold, validate, lint and test agent skills (SKILL.md) — like unit tests for your skill descriptions.**

Writing an agent skill is easy. Getting the agent to actually *load* it is not:
the description field is the only signal the router sees, the spec has silent
truncation limits, and there is no feedback loop. skillvet turns skill
authoring from guesswork into engineering.

```
pip install skill-inspect     # or: uvx skill-inspect <cmd>  (zero install)
```

## Why not skillcheck / skillbench?

The ecosystem already has good tools, but they answer different questions:

| Tool | Question it answers |
|---|---|
| `skillcheck` | "Is my SKILL.md spec-compliant?" (static analysis) |
| `skillbench` | "Does my skill complete tasks in a real agent?" (end-to-end eval) |
| **skillvet** | **"Will the agent actually *pick* my skill when the user asks?"** (trigger rate) |

skillvet's focus is the step *before* execution: the routing decision. It
measures how often your skill gets chosen for phrasings it should handle —
and how often it fires on adjacent requests it shouldn't. It also works in
both English and Chinese skill contexts, where trigger vocabulary differs
significantly. Use it alongside the others; they are complementary.

## Commands

### `skillvet new` — scaffold with best practices baked in

```
skillvet new xhs-writer
```

Interactively asks what the skill does and **three ways users actually phrase
the request**, then generates a spec-compliant directory with those phrasings
already embedded in the description — the single biggest factor in trigger rate.

Templates: `basic`, `with-scripts`, `with-references`.

### `skillvet validate` — spec checks, offline, CI-friendly

```
skillvet validate ./skills/          # one skill or a whole collection
skillvet validate . --json           # machine-readable, exit code 1 on error
```

Checks include:

- `SKILL.md` present with exact casing (`skill.md` fails silently in agents)
- `name` required, ≤ 64 chars, kebab-case, matches the directory name
- `description` required, ≤ 1024 chars (beyond this it is *silently truncated*)
- `description + when_to_use` ≤ 1536 chars (listing truncation)
- every file referenced in the body (`references/…`, `scripts/…`) actually exists
- risky patterns in bundled scripts (`rm -rf`, `curl | sh`, `shell=True`)
- unknown frontmatter fields

### `skillvet lint` — best-practice checks

`validate` checks correctness; `lint` checks quality:

- description states **when to use**, not just what it is
- description embeds quoted example phrasings
- body stays lean (~≤150 lines), detail moved to `references/`
- explicit guardrails against the model inventing facts

### `skillvet test` — measure trigger rate with an LLM

The differentiator. An agent decides what to load by scanning a listing of
`name + description` — so we reproduce that exact decision context as a prompt
and let any OpenAI-compatible model play the router:

```yaml
# skillvet.cases.yml (in your skill directory)
cases:
  - input: "帮我把这篇笔记改成小红书风格"
    expect: trigger
  - input: "帮我写公众号推文"
    expect: no_trigger     # adjacent request — must NOT trigger
```

```
export SKILLVET_API_KEY=...      # or OPENAI_API_KEY; --base-url for any compatible endpoint
skillvet test ./xhs-writer --model deepseek-chat
skillvet test ./xhs-writer --with ./other-skill   # compete against installed skills
```

Output:

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ input                       ┃ expected   ┃ router chose ┃ result ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━┩
│ 帮我把这篇笔记改成小红书风格 │ trigger    │ xhs-writer   │   ✓    │
│ 发个xhs                     │ trigger    │ NONE         │   ✗    │
│ 帮我写公众号推文            │ no_trigger │ NONE         │   ✓    │
└─────────────────────────────┴────────────┴──────────────┴────────┘

passed 2/3  ·  trigger rate 50%  ·  false-positive rate 0%

suggestion: these phrasings failed to trigger: "发个xhs"
add them (or their vocabulary) verbatim to the skill description, then re-run.
```

> **Honest scope:** the simulated router is an *approximation* of real agent
> routing. Use it to iterate on descriptions — not as a guarantee of in-agent
> behavior.

## Use it in CI

`validate --json` exits non-zero on spec errors, so any skill repo can gate on it.
A ready-made GitHub Action is on the roadmap — PRs welcome.

## Development

```
git clone https://github.com/lfnfromchina-bot/skilldoctor && cd skilldoctor
pip install -e '.[dev]'
pytest
```

Layout: `parser` (SKILL.md parsing) · `validator` / `linter` (pure functions,
importable as a library) · `tester` + `router_prompt` (LLM router simulation) ·
`scaffolder` (templates) · `cli` / `report` (typer + rich).

## License

MIT

---

## 中文说明

skillvet 解决写 Agent Skill 时的三个痛点：**description 写不好就触发不了**、
**格式规范写错了静默失效**、**改完没法回归测试**。

- `skillvet new`：脚手架，生成时自动把"用户的 3 种说法"嵌进 description（触发率的关键）
- `skillvet validate`：对照 SKILL.md 规范逐条校验，支持 `--json` 接 CI
- `skillvet lint`：最佳实践检查（触发措辞、渐进式披露、防护栏）
- `skillvet test`：用 LLM 模拟 agent 的 skill 路由决策，量化触发率和误触率，让调 description 像写单元测试一样

`skillvet test` 支持任何 OpenAI 兼容接口（DeepSeek、Kimi、本地模型均可），
一次测试成本不到一分钱。
