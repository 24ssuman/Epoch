# Frontend

React + TypeScript, Three.js/WebGL2 and locally bundled Lucide icons. `src/App.tsx` owns the synchronized clock, settings, UI and stale-response rejection. `src/Sky.tsx` renders the ground sky with reusable buffers/materials/body meshes. `src/style.css` provides responsive layout.

Build with `npm run build --prefix frontend` from the workspace. The backend serves dist/ on localhost. Development: run the backend and `npm run dev --prefix frontend`; Vite proxies /api locally. No CDN scripts, fonts or analytics are used.

The UI supports only the From Earth perspective. `MoonPhase.tsx` supplies the collapsible Moon tab from the currently accepted snapshot, with no extra requests. `playback.ts` owns deterministic 100 ms samples and the single-flight/latest-target request queue. Run `npm test --prefix frontend` for transport/clock regressions.
