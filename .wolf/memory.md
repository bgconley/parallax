# Memory

> Chronological action log. Hooks and AI append to this file automatically.
> Old sessions are consolidated by the daemon weekly.

| 23:27 | Recorded environment routing preference: backend/integration/end-of-phase validation on GPU node; Mac for unit tests and UI/Xcode/Figma/Playwright work | AGENTS.md, .wolf/OPENWOLF.md, .wolf/cerebrum.md | preference saved | ~80 |
| 23:37 | Recorded GPU node SSH access command for backend operations and validation | AGENTS.md, .wolf/OPENWOLF.md, .wolf/cerebrum.md | access note saved | ~20 |
| 01:06 | Recorded correction: review canonical Parallax artifacts before inferring infrastructure from GPU-node state; ZFS must follow artifact plan/script | AGENTS.md, .wolf/OPENWOLF.md, .wolf/cerebrum.md | process rule saved | ~65 |
| 01:14 | Added GPU-node storage setup script with canonical Parallax ZFS datasets, explicit recordsizes, and /tank/repos/parallax plus /tank/venvs/parallax project paths | scripts/setup_gpu_node_storage.sh, docs/architecture/gpu_node_storage.md, AGENTS.md, .wolf/OPENWOLF.md, .wolf/cerebrum.md | storage bootstrap documented | ~110 |
| 01:37 | Added permission-only GPU-node script so Parallax runtime ownership can be applied safely after datasets exist | scripts/apply_gpu_node_permissions.sh, scripts/setup_gpu_node_storage.sh, docs/architecture/gpu_node_storage.md | permission workflow codified | ~90 |
| 01:45 | Verified live GPU-node Parallax datasets, mountpoints, recordsize properties, and ownership/mode policy under /srv/parallax | /srv/parallax, tank/parallax, /tank/repos/parallax, /tank/venvs/parallax | storage state verified; /tank/venvs ext4 accepted | ~100 |
| 01:50 | Staged, validated, committed, and pushed Phase 0/1 bootstrap plus GPU storage artifacts to origin/master | commit 2a133d5, scripts, docs, services/api, packages, migrations | remote updated and working tree clean | ~90 |
| 01:58 | Recorded remote sudo TTY requirement, .DS_Store validation gotcha, verified storage permissions, and venv filesystem exception | AGENTS.md, .wolf/OPENWOLF.md, .wolf/cerebrum.md, .wolf/buglog.json | session context refreshed | ~110 |
