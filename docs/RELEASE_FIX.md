# Release Version Fix Guide

## Problem

The GitHub repository has version **3.3.0** as documented in:
- `pyproject.toml` (line 7: `version = "3.3.0"`)
- `README.md` (line 15: `*version 3.3.0*`)
- `docs/changelog/CHANGELOG.md` (latest entry: `## [3.3.0] - 2025-12-06`)

However, the GitHub API's "latest release" endpoint incorrectly returns `release-v3.0` as the latest release instead of `release-v3-latest` (v3.3.0).

### Current GitHub Releases

| Tag Name | Version | Published Date | Status |
|----------|---------|----------------|--------|
| `release-v3-latest` | **v3.3.0** | 2025-12-11T08:00:35Z | **Should be latest** |
| `release-v3.2` | v3.2 | 2025-12-11T08:00:43Z | Older |
| `release-v3.1` | v3.1 | 2025-12-11T08:00:51Z | Older |
| `release-v3.0` | v3.0 | 2025-12-11T08:00:57Z | **Incorrectly marked as latest** |

## Root Cause

GitHub marks the **most recently published** release as "latest", not the release with the highest version number. Since `release-v3.0` was published last (at 08:00:57), it's incorrectly marked as the latest release, even though v3.3.0 is the actual current version.

## Solution

You need to manually update the GitHub release settings to mark `release-v3-latest` (v3.3.0) as the latest release.

### Steps to Fix (via GitHub Web UI)

1. **Go to Releases Page**
   ```
   https://github.com/amuzetnoM/gold_standard/releases
   ```

2. **Edit the v3.3.0 Release**
   - Find the `release-v3-latest` (Gold Standard v3.3.0) release
   - Click the **"Edit"** button (pencil icon)

3. **Mark as Latest**
   - Check the box that says **"Set as the latest release"**
   - Click **"Update release"**

4. **Verify**
   - Go back to the releases page
   - Confirm that `release-v3-latest` (v3.3.0) now shows a **"Latest"** badge
   - Test the API endpoint:
     ```bash
     curl -s https://api.github.com/repos/amuzetnoM/gold_standard/releases/latest | jq '.tag_name'
     ```
     Should return: `"release-v3-latest"`

## Alternative: Delete and Recreate

If the "Set as latest" option doesn't work, you can:

1. **Create a new release** with tag `v3.3.0` (or keep `release-v3-latest`)
2. **Ensure it's published AFTER all other releases** (delete and recreate if needed)
3. **Check the "Set as the latest release" option** when creating

## Recommended Tag Naming Convention

For future releases, use consistent semantic versioning tags:
- ✅ `v3.3.0`, `v3.4.0`, `v4.0.0` (recommended)
- ❌ `release-v3-latest` (ambiguous)
- ❌ `release-v3.0`, `release-v3.1` (inconsistent)

This ensures GitHub correctly orders releases by version number.

## Verification Checklist

After fixing:
- [ ] GitHub releases page shows v3.3.0 with "Latest" badge
- [ ] API returns correct version: `curl https://api.github.com/repos/amuzetnoM/gold_standard/releases/latest | jq '.tag_name'`
- [ ] README.md version matches (currently ✅ correct: v3.3.0)
- [ ] pyproject.toml version matches (currently ✅ correct: v3.3.0)
- [ ] CHANGELOG.md has v3.3.0 as top entry (currently ✅ correct)

## References

- [GitHub Docs: Managing releases](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)
- [Semantic Versioning](https://semver.org/)
