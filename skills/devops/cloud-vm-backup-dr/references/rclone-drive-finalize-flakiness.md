# rclone -> Google Drive: finalize flakiness (Jeddah VM, Sep 2026)

Nightly ~1.8 GiB archive reaches 100 % of the body, then the finalize/commit stalls and rclone
silently re-sends the whole file from byte 0. No ERROR line at any verbosity, no retry line,
quota free (`rclone about gdrive:` used 4.96 of 15 GiB, trashed 0).

## Path comparison
- **Resumable** (`--drive-upload-cutoff 8M --drive-chunk-size 32M`): 0 commits in 3 nights.
  After 100 % it trickles at 5-800 B/s - slow enough that `--timeout` keeps resetting and the run
  never aborts; only the wall stops it.
- **Single-shot** (`--drive-upload-cutoff 2G --transfers 1 --retries 2 --low-level-retries 15`):
  commits, usually after 2-3 whole-file attempts. Now strategy #1; walls `SINGLE_WALL=2700`,
  `RESUMABLE_WALL=1500`.

## Decisive probe - this is NOT a size problem
```bash
dd if=/dev/zero of=/tmp/probe20.bin bs=1M count=20
timeout 300 rclone copy /tmp/probe20.bin gdrive:Hermes-Telegram-Backup/ \
  --drive-upload-cutoff 2G --transfers 1 --retries 2 --low-level-retries 15 \
  --timeout 15m --contimeout 60s --stats 5s --stats-one-line -v --log-file /tmp/probe20.log
```
2026-09-15: `RCLONE_EXIT=0` after 2m53s, **3 whole-file attempts for 20 MiB** (2-5 MiB/s bursts
decaying to 65 KiB/s at each finalize, then a re-send from byte 0), object landed and md5-matched.
Since 20 MiB fails exactly like 1.8 GiB, splitting archives into smaller parts is NOT the fix -
attribute the finalize failure first.

## Log / counter traps
- `--stats-one-line` "x / y" is NOT an attempt counter; its shape differs run to run (09-14 ended
  `3.451/3.451 GiB` for a 1.726 GiB file = 2.0x; 09-15 `7.137/7.137` for 1.784 GiB = 4.0x; the
  20 MiB probe opened at `20/40 MiB` before a byte moved). Reading "4x" as "4 passes" was wrong.
- It also counts post-landing re-sends: an object is already listed by name while rclone is still
  re-sending it, so a name match proves nothing about the commit.

## Proving the off-VM copy
1. `rclone lsf gdrive:Hermes-Telegram-Backup/ --include 'sanad-backup-*.gpg'` - name (necessary)
2. `~/ops/verify/drive_md5_parity.py <local-archive>` - content md5, no download (sufficient)
3. `rclone check <local-dir> gdrive:Hermes-Telegram-Backup/ --include 'sanad-backup-*.gpg'`

## Outstanding attribution (next flaky night)
`--dump=headers` (never `-vv` - it logs the OAuth token) to attribute the finalize failure; repair
path that skips the dump entirely: `sudo -E bash backup.sh --upload-only`.
