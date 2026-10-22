# Frontend regression checks

Run `npm test --prefix frontend`. Tests transpile the production TypeScript playback scheduler in memory with the installed compiler; no extra packages or runtime downloads are required. They cover exact sampling, reverse replay, delayed/aborted responses, latest-target coalescing, and generation invalidation.

`moonlight.test.mjs` checks referenced lunar phase/magnitude-to-flux scaling, inverse-square distance, exposure, daylight and horizon/atmosphere behavior.
