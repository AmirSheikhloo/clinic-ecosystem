# Windows: fetch `development/clinic-operations` into an isolated worktree

Non-production, synthetic data only. This never touches `main`, PR #6 or your other
branches, and never overwrites uncommitted work in your existing clone.

## 1. Fetch the branch into a new worktree (PowerShell)

```powershell
Set-Location C:\Users\amir\Documents\clinic-ecosystem      # your existing clone
git fetch origin development/clinic-operations
git log --oneline -1 origin/development/clinic-operations   # compare with the SHA in the handoff report

$wt = "C:\Users\amir\Documents\clinic-ecosystem-operations"
if (Test-Path $wt) { throw "Worktree path already exists: $wt" }
git worktree add --detach $wt origin/development/clinic-operations
Set-Location $wt
git status --short                                           # must print nothing
```

`--detach` keeps your local branch names untouched. To work on it later, create a new
local branch from the detached HEAD (`git switch -c local/operations-review`).
To remove everything afterwards: `git worktree remove $wt --force`.

## 2. Start the disposable stack

Prerequisites: Docker Desktop running, Python 3.12, Node.js 22 (all on `PATH`).

One command, repeatable. It creates `.venv` on first use, runs `pip install -e`, `npm ci` and
`npm run build` only when their inputs changed (hash stamps in `.preview-cache\`, git-ignored),
then starts the stack:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_preview.ps1
# add -Force to ignore the stamps and reinstall/rebuild everything
```

Manual equivalent:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "$PWD\src;$PWD"
python scripts\prepare_preview.py          # skips unchanged steps; --check only reports
python scripts\start_preview_stack.py
```

The launcher puts `src` on `PYTHONPATH` for the API process, resolves `npm` through `shutil.which`
(so `npm.cmd` works) and starts Next.js with `node` directly when the local build exists.

The script starts a throw-away PostgreSQL 15 container, applies migrations `tp0001`-`tp0007`,
seeds synthetic data, starts the API and the Next.js panel, and writes
`P03_HANDOFF\beta_panel_preview\preview.env` (passwords; git-ignored; never commit or share it)
and `PREVIEW_URL.txt` (URLs and login names only).

Open `PANEL_URL` from `PREVIEW_URL.txt`. Logins from `preview.env`:

| Persona | Variables | What to look at |
|---------|-----------|-----------------|
| Receptionist | `BETA01B_RECEPTIONIST_*` | Desk, patients, calendar; no admin screens |
| Manager | `BETA02_MANAGER_*` | Staff, access, catalog admin, patient profile |
| Owner | `BETA02_OWNER_*` | Everything the manager has, plus governance editing |
| Deputy admin | `BETA02_DEPUTY_*` | Roles and role assignment only |

## 3. Reset behaviour

All data lives in the disposable container. Stop the script (Ctrl+C) and the container
and all data are deleted; the next start reseeds from scratch. Nothing persists between runs.

## 4. Verify

```powershell
Set-Location beta-panel
npm test; npx tsc --noEmit; npm run lint
Set-Location ..
$env:PYTHONPATH = "$PWD\src;$PWD"
python scripts\prepare_preview.py                    # make sure the production build is current
python -m tests.e2e.beta01b.run_browser_e2e
python -m pytest tests\unit tests\integration -q
```

## Layout geometry and preferences (Linux-validated)

Linux cloud agent validated: shell geometry suite, preferences localStorage, dense calendar lanes.
Windows behavior of the same UI is **unverified in this environment**. Use `scripts\start_preview.ps1` as before; no new Windows-only steps.
Do not treat browser preferences as synchronized clinic settings.

