# Third-party tooling requested for this project

**Reviewed/installed locally:** 2026-11-19 UTC. These dependencies are development aids, not part of the competition inference submission.

| Repository | Local checkout | Revision | Install/use status | Decision |
|---|---|---|---|---|
| [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | `.external/agent-skills` (ignored by Git) | `e997ac5b9a74eab332d5e9793bb38a38c8cfdd74` | Cloned and reviewed. The repo is primarily Markdown workflow skills plus host-specific plugin manifests and CLI instructions. | Arena Agent Mode does not expose a supported way to activate third-party agent plugins inside this session. The planning, incremental implementation and test-first practices are being followed manually; no unsupported global install was attempted. |
| [TinyAGI/fractals](https://github.com/TinyAGI/fractals) | `.external/fractals` (ignored by Git) | `c0d939706c6b6aa05b1fcf3a864f9e4a30fc3603` | Cloned; `npm ci --ignore-scripts` completed. | Not launched. README describes it as experimental, requires OpenAI API credentials and delegates execution to Claude/Codex CLI; its execution example uses `--dangerously-skip-permissions`. It is not needed for this scientific pipeline and would be inappropriate to run automatically here. |

`npm ci` reported four dependency advisories (two high, one moderate, one low; available fixes reported). Do not start Fractals or expose credentials until those are reviewed and fixed. `.external/` is intentionally gitignored: third-party source and installed dependencies must not enter the CASMI solution or Kaggle submission.

## Using the workflows safely

We apply the useful, non-executable practices: break work into atomic tasks, keep explicit acceptance criteria, use grouped validation, and run tests before claiming results. The Fractals tree can be a visual planning concept, but this repository remains the source of truth for experiments. Third-party agent code is never allowed to bypass review, access competition secrets, or make unverified leaderboard claims.
