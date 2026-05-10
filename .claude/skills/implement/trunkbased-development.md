# Trunk-Based Development

## The branching rule

**Commit directly to `main`.** Never create a branch.

## Hiding incomplete features

Use a feature flag only when the acceptance criteria require hiding the change at runtime.

Define all flags as `const bool` in one central file:

```dart
// lib/core/feature_flags.dart
abstract final class FeatureFlags {
  static const bool newCheckoutFlow = false;
}
```

Guard the feature at the call site:

```dart
if (FeatureFlags.newCheckoutFlow) {
  // new path
} else {
  // existing path
}
```

- Ship with the flag `false`; flip to `true` to release
- Delete the flag and its dead code ~1 month after release

## Commit discipline

Every commit must leave `main` in a releasable state. Integrate frequently — do not let local changes age.

After every push, check CI with `gh run list --branch main --limit 1` (then `gh run view <id>` for details). If CI turns red on `main`, fix or revert immediately — green `main` is the project's release branch.

## Releases

Always release from `main`. There are no release branches.
