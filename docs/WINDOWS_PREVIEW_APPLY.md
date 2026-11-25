# Windows preview apply — clinic panel increment

**Baseline commit:** `2aa3de8bfa7f9e26fd4ab331807c5005784e040b` (`fix/beta01b-security-deps`)
**Do not** merge, push, or alter PR #6. Apply only in an isolated local worktree.

## Apply the binary patch (PowerShell)

From your Windows clone root (example: `C:\Users\amir\Documents\clinic-ecosystem`):

```powershell
# 1) Verify you have the baseline commit
git fetch origin fix/beta01b-security-deps
git rev-parse 2aa3de8bfa7f9e26fd4ab331807c5005784e040b

# 2) Isolated worktree (keeps your other branches untouched)
$wt = "C:\Users\amir\Documents\clinic-ecosystem-beta-panel"
git worktree add -b local/beta-clinic-panel-preview $wt 2aa3de8bfa7f9e26fd4ab331807c5005784e040b
Set-Location $wt

# 3) Verify patch checksum (replace path to the downloaded artifact)
$patch = "$env:USERPROFILE\Downloads\clinic_panel_from_2aa3de8_binary.patch"
Get-FileHash $patch -Algorithm SHA256

# 4) Dry-run, then apply (binary-capable)
git apply --check --binary $patch
git apply --binary $patch
git add -A
git status
git commit -m "feat(beta-panel): apply clinic panel preview increment"
```

If `git apply` reports conflicts, stop and do not force. Re-check that the worktree tip is exactly `2aa3de8…`.

## Start disposable preview (Docker Desktop + Python 3.12 + Node)

Prerequisites: Docker Desktop running, Python 3.12 venv with project deps, Node.js for `beta-panel`.

```powershell
Set-Location C:\Users\amir\Documents\clinic-ecosystem-beta-panel
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Set-Location beta-panel
npm ci
npm run build
Set-Location ..
python scripts\start_preview_stack.py
```

The script writes `P03_HANDOFF\beta_panel_preview\preview.env` (mode-restricted on Unix; treat as secret on Windows) and prints `PANEL_URL` / `API_URL`.

Open the printed `PANEL_URL` (login). Use credentials from `preview.env` only on the local disposable stack — never commit that file.

## Smoke checks

```powershell
Set-Location beta-panel
npm test
npx tsc --noEmit
npm run lint
# With preview.env vars loaded into the session:
npm run test:e2e
```

Backend beta01b (requires Docker):

```powershell
pytest tests\unit\test_beta01b_*.py tests\integration\test_beta01b_reception_api.py -v
```
