# Device log retention

Deployed October 3, 2026. Keep private drive archives off Git; the latest analyzed drive remains saved on the maintenance computer.

| Device | Before | After | Retention |
| --- | --- | --- | --- |
| comma data partition | 8.9 GiB free; 67 GiB recordings | 56 GiB free; 20 GiB recordings | Hourly offroad cleanup, 20 GiB recording budget and 20 GiB free-space target |
| Jetson NVMe | 1.7 TiB free; 206.7 MiB journal | 1.7 TiB free; 92.5 MiB journal | 128 MiB journal limit; hourly logrotate with 16 MiB system-log rotation trigger |
| Pixel | Not connected to ADB during this audit | Not checked or changed | Recheck when connected |

The comma cleanup removed 575 old segments (46.26 GiB). A repeat preview selected zero further deletions. Models, prepared engines, settings, updater staging, rollback backups, and the two latest routes were preserved. Comma application logs were 357 MiB and already rotate at 2,500 files of approximately 256 KiB each; no extra cleaner was added for those files.

## Comma

`comma_log_retention.py` defaults to a preview; `--apply` deletes old recording segments. It only operates when `/data/params/d/IsOffroad` is `1`, checks that state again before each deletion, skips locked segments and symlinks, and protects the latest two routes plus manually preserved segments and their two predecessors. Hexadecimal route counters determine ordering, not directory modification times. Legacy dated routes sort before counter-based routes.

The 20 GiB limits are **targets**, not hard caps: onroad operation, locked files, or protected recordings can prevent reaching them. The native low-space deleter remains enabled as the original emergency safeguard and retains its own deletion policy. An ignition transition can occur during a single directory deletion, so only old, unlocked routes are eligible. Recording budget calculations use file lengths; filesystem allocation may differ slightly.

Copy the Python script to `/data/maintenance/comma_log_retention.py`, and copy the service and timer to `/etc/systemd/system/`. AGNOS normally mounts `/` read-only: temporarily remount it writable for installation, then restore it read-only even if installation fails. Run:

```sh
python3 /data/maintenance/comma_log_retention.py
sudo systemctl daemon-reload
sudo systemctl enable --now clarity-log-retention.timer
sudo systemctl start clarity-log-retention.service
systemctl list-timers clarity-log-retention.timer
journalctl -u clarity-log-retention.service -n 10 --no-pager
df -h /data
```

Run `python3 test_comma_log_retention.py` alongside the script to test preview behavior, offroad gating, protected and locked recordings, hexadecimal ordering, and external symlink protection. All six tests passed on the comma.

Disable future cleanup with `sudo systemctl disable --now clarity-log-retention.timer`. Already deleted recordings cannot be recovered. OS image replacement may remove the units; check/reinstall the timer after an AGNOS upgrade. The data script is outside the driving checkout.

## Jetson

Installed the missing Ubuntu `logrotate` package; the existing rsyslog rotation configuration had no executable or timer to run it. No general package upgrade was performed.

1. Install `logrotate` with apt.
2. Install `70-clarity-retention.conf` in `/etc/systemd/journald.conf.d/`.
3. Back up `/etc/logrotate.d/rsyslog`, then add `maxsize 16M` inside its existing block. Keep `weekly`, `rotate 4`, compression, and the rsyslog postrotate hook. Do not duplicate the stanza.
4. Install `logrotate-timer.conf` as `/etc/systemd/system/logrotate.timer.d/clarity.conf`.
5. Run `sudo logrotate --debug /etc/logrotate.conf` and resolve errors before activating.

```sh
sudo systemctl daemon-reload
sudo systemctl restart systemd-journald
sudo systemctl enable --now logrotate.timer
sudo systemctl restart logrotate.timer
sudo journalctl --sync --rotate
sudo journalctl --vacuum-size=96M
sudo logrotate --force /etc/logrotate.conf
sudo apt-get clean
journalctl --disk-usage
systemctl list-timers logrotate.timer
systemctl is-active jetlink-server
```

The journal sync interval is 30 seconds to improve persistence after power removal; this cannot guarantee recovery after an abrupt cut. Size-based journal retention avoids relying on the Jetson's pre-NTP boot clock. Logrotate checks hourly, so a busy log can exceed 16 MiB between checks. Existing rotated files may also be larger until they age out. Total `/var/log` fell from 286 MiB to 171 MiB; apt cache is now 20 KiB. JetLink remained active, with 2.2 GiB of models and 3.6 GiB of engines untouched.

The original rsyslog configuration is backed up at `/var/backups/clarity-log-retention/rsyslog.before`. To undo the changes, restore that file, remove only the two Clarity override files, reload systemd, and restart journald and the logrotate timer. The earlier journal override remains in place underneath ours. Keep logrotate installed so packaged rotation policies continue working.
