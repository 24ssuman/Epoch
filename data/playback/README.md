# Stored playback frames

`frames.sqlite3` stores compressed completed exact sky snapshots, including their scientific metadata. Repeated requests with matching TT date (rounded to 10⁻⁸ day), observer, rotation offset, catalog limit, magnitude cutoff and model revision reuse the stored frame across server restarts. No interpolation of apparent directions is introduced. New observer settings or dates need new projections even when trajectories already exist.

Scientific source/code changes invalidate affected keys; worker progress does not. Only accepted trajectory chunks covering the requested epoch affect its key. Existing records are preserved. New storage stops at 512 MB of compressed frame payload or the workspace 10 GB guard. Old files are not automatically deleted. A storage-limit explanation appears in calculation details.

The storage-coverage endpoint indexes existing frame dates in a separate SQLite table without changing payloads. Date bounds include retained older-model frames; these may need recalculation. The calculation drawer reports these discrete samples separately from the merged duration of validated background trajectory files.
