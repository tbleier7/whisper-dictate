---
name: implement
description: Full implementation workflow for any code change. Combines trunk-based development with an outer acceptance test driven loop per acceptance criterion and a (unit) test driven inner loop. Use whenever the user asks to implement, fix, build, add, or change anything in the codebase.
---

# Implement

Single entry point for all code changes. Every change follows this workflow top to bottom.

## Phase 1: Understand

- Read the task and its acceptance criteria from issue number (`gh issue view <n>`), freeform description, or conversation context
- If acceptance criteria are missing or unclear from any source, invoke the `grill-me` skill to draw them out, draft a list, and confirm with the user before continuing
- Identify affected layer: UI, state, repository, backend
- Resolve any ambiguity about the existing codebase from the codebase itself if possible

## Phase 2: Outer loop

- Work through one acceptance criterion at a time, starting with what you see as the most fitting regarding blockers and dependencies.
- Write an acceptance test at the highest level that actually exercises the criterion — widget test for single-screen UI, integration test for cross-screen flows, unit/repository test for pure logic. Skip only when the change has no observable behavior (rename, deps, CI, docs) and the existing suite still covers the affected area
- Design the public interface / API change — see [interface design](interface-design.md) and [deep modules](deep-modules.md)
- List behaviors to test (not implementation steps)
- Always use [trunk-based development](trunkbased-development.md): commit directly to `main`. Use a feature flag only when the acceptance criteria call for hiding the change at runtime.

## Phase 3: Inner TDD Loop

The acceptance test from Phase 2 stays RED until every behavior under it is implemented. Inside that, drive each behavior with a tight unit-test cycle:

```
RED:      one failing unit test for one behavior
GREEN:    minimal code to pass it
REFACTOR: clean up while staying green
```

Repeat until the acceptance test goes green. See [TDD](tdd.md) for full rules, mocking guidelines, and refactoring candidates.


## Phase 4: Commit

After an acceptance criterion is fully implemented:

1. If any `@freezed` or `@riverpod` class changed: `dart run build_runner build --delete-conflicting-outputs`
2. `flutter analyze` — zero issues
3. `flutter test` — all pass (this includes the acceptance test from Phase 2)
4. Commit and push to `main`
5. Verify CI stays green (see [trunk-based development](trunkbased-development.md))
