# Project context

This is the `vital-mobile` repo — the Expo (React Native) mobile app for the Vital wellness brand. Phase 1.

## Required reading before any task

The full build specification is at `../BUILD-SPEC.md`. Read sections 1, 2, 5, and 6 (mobile prompts P6–P13).

## Constraints

- Expo (managed workflow) + TypeScript strict
- expo-router for navigation
- TanStack Query for server state
- Design system: tokens in src/theme/tokens.ts, never inline hex
- Typography: Fraunces (display) + Geist Sans (UI) + Geist Mono (numbers)
- No purple/pink gradients, no glassmorphism, no neon — see Section 5
- API types are codegen from ../kyros-backend/openapi.json via openapi-typescript
- Local notifications only in Phase 1 (no push, no FCM/APNs)
