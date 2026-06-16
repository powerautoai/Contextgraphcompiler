# M8.4 GitHub Handoff

## 1. PR Title

### Recommended
`Add M8.4 multi-platform release dist, manifest, and size-budget gate`

### Alternative
`Productize M8.4 with 3-platform build matrix, dist manifest, and release assets`

## 2. PR Body

```md
## Summary

This PR upgrades `M8.4` from a host-only `cgc build` validation into a release-ready productization gate.

It now validates:

- real multi-platform build evidence for `windows`, `macos`, and `linux`
- aggregated `build_matrix.json`
- release dist convergence under `CGC_Release/dist/{windows,macos,linux}`
- `build_matrix_manifest.json`
- per-platform package size policy with `soft target` and `hard limit`
- GitHub Actions and Jenkins release-asset collection flow

## What Changed

### Gate Contract

- extend `m84_cgc_build_release_acceptance` to include:
  - `cgc_build_release_contract`
  - `build_matrix_contract`
  - `build_dist_manifest_contract`
  - `artifact_size_budget`
  - `windows_artifact_size_budget`
  - `macos_artifact_size_budget`
  - `linux_artifact_size_budget`

### Gate Runtime

- add `build_dist_manifest_contract` validation in `CGC_Release/m8_gate.py`
- upgrade `artifact_size_budget` from a single hard cutoff to:
  - `PASS` within soft target
  - `WARN` above soft target
  - `FAIL` above hard limit
- expose `budget_status`, `size_budget_level`, and `executable_budget_level` in gate output

### Build Dist and Release Assets

- add `scripts/ci/collect_release_dist.py`
- collect per-platform build outputs into:
  - `CGC_Release/dist/windows`
  - `CGC_Release/dist/macos`
  - `CGC_Release/dist/linux`
- generate:
  - `CGC_Release/dist/build_matrix_manifest.json`
  - `CGC_Release/dist/release_assets/cgc-windows.zip`
  - `CGC_Release/dist/release_assets/cgc-macos.zip`
  - `CGC_Release/dist/release_assets/cgc-linux.tar.gz`

### CI / Jenkins

- update `.github/workflows/m84-build-matrix.yml` to:
  - download per-platform reports
  - download per-platform build outputs
  - aggregate `build_matrix.json`
  - collect release dist
  - run `M8.4-only` gate
  - publish release assets on tag builds
- update `Jenkinsfile` with the same matrix aggregation and dist collection flow

## Validation

Validated locally with smoke evidence:

- `macos` report passes size budget contract
- `build_matrix_contract` fails when `windows`/`linux` evidence is missing
- `build_dist_manifest_contract` fails when dist/asset coverage is incomplete

This is expected and proves the gate now rejects incomplete 3-platform release evidence.

## Key Files

- `CGC_Release/m8_gate.yaml`
- `CGC_Release/m8_gate.py`
- `scripts/ci/render_m84_gate_config.py`
- `scripts/ci/collect_release_dist.py`
- `.github/workflows/m84-build-matrix.yml`
- `Jenkinsfile`

## Notes

- full `M8.4 PASS` now requires actual CI-generated artifacts from all three target platforms
- local single-host smoke can validate logic correctness, but cannot replace true 3-platform release evidence
```

## 3. Tag / Release Title

### Recommended
`M8.4 Release Build Matrix and Dist Manifest`

### If using semantic tag text
`<tag>: M8.4 multi-platform release build`

## 4. Release Notes

```md
## M8.4 Release Build Matrix and Dist Manifest

This release turns `M8.4` into a real release-delivery gate instead of a host-only build check.

### Highlights

- validates real build evidence on `windows`, `macos`, and `linux`
- aggregates per-platform reports into `build_matrix.json`
- collects release-ready artifacts under `CGC_Release/dist/{windows,macos,linux}`
- generates `build_matrix_manifest.json`
- publishes release assets from CI on tag builds
- enforces per-platform package size policy with `soft target`, `hard limit`, and `warning/fail` semantics

### Acceptance Contract

`m84_cgc_build_release_acceptance` now requires all of the following:

- `cgc_build_release_contract`
- `build_matrix_contract`
- `build_dist_manifest_contract`
- `artifact_size_budget`
- `windows_artifact_size_budget`
- `macos_artifact_size_budget`
- `linux_artifact_size_budget`

### Release Artifacts

CI now converges release outputs into:

- `CGC_Release/dist/windows`
- `CGC_Release/dist/macos`
- `CGC_Release/dist/linux`
- `CGC_Release/dist/build_matrix_manifest.json`
- `CGC_Release/dist/release_assets/cgc-windows.zip`
- `CGC_Release/dist/release_assets/cgc-macos.zip`
- `CGC_Release/dist/release_assets/cgc-linux.tar.gz`

### Operational Meaning

This release closes the gap between:

- "the build command exists"
- "the product is truly releaseable across 3 platforms"

`M8.4 PASS` now means the project has:

- host build evidence
- three-platform matrix evidence
- dist convergence evidence
- release asset evidence
- package-size compliance evidence

### Remaining Requirement

Local smoke verification proves gate logic and failure semantics.

A final full `PASS` still requires CI runners to produce real artifacts for:

- `windows`
- `macos`
- `linux`
```

## 5. Whitepaper / Gate Mapping

Use the following wording when aligning release notes with the formal gate whitepaper.

### M8 Overall

- `M8` = `M7.5 API compatibility` + `M8 cgc command acceptance`

### M8.1

- section name: `m81_m75_claude_dual_acceptance`
- meaning: `M7.5 API compatibility` + `Claude Code`

### M8.2

- section name: `m82_cgc_run_route_dual_acceptance`
- meaning: `cgc run local success` + `route decision / M7.3 takeover evidence`

### M8.3

- section name: `m83_serve_streaming_takeover_acceptance`
- meaning: `serve streaming local success` + `M7.3 takeover streaming evidence`

### M8.4

- section name: `m84_cgc_build_release_acceptance`
- meaning: `host build` + `3-platform matrix evidence` + `dist manifest` + `per-platform warning/fail size budget`

### Whitepaper Wording for M8.4

Recommended wording:

> M8.4 does not only verify that `cgc build` can execute on the current host. It is a formal release acceptance gate that requires real build evidence for `windows`, `macos`, and `linux`, aggregated matrix evidence, converged release dist structure under `CGC_Release/dist`, release-asset packaging, and per-platform package-size governance with `soft target`, `hard limit`, and `warning/fail` semantics.

## 6. Quick References

- Gate config: `CGC_Release/m8_gate.yaml`
- Gate runtime: `CGC_Release/m8_gate.py`
- Dist collector: `scripts/ci/collect_release_dist.py`
- CI workflow: `.github/workflows/m84-build-matrix.yml`
- Jenkins pipeline: `Jenkinsfile`
