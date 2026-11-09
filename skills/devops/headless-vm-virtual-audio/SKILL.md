---
name: headless-vm-virtual-audio
description: Use when a headless VM needs a mic or audio devices.
---

# Virtual audio devices on a soundcard-less VM

## When to use
Any task that needs a microphone or speaker on a headless VM: joining meetings as an attendee,
recording system audio for transcription, feeding TTS voice into an app that expects a mic.
Symptom that triggers this: `pactl` works but recordings are `-91.0 dB` (digital silence),
`/dev/snd` is empty, `cat /proc/asound/cards` shows nothing, apps report
"Unrecognized speaker" / no input device.

## Root cause
A VM with no sound hardware has no ALSA card, so PulseAudio/PipeWire only provide a
fallback `auto_null` sink and **no input source at all**. Browsers can't open a microphone and
WebRTC clients (Zoom web) may never start receive audio, so capture is pure silence.

## Procedure (verified on Ubuntu 24.04 aarch64, PipeWire, sudo available)

1. Load kernel dummy devices and pin their card indices:
   ```bash
   sudo modprobe snd-aloop && sudo modprobe snd-dummy
   printf 'snd-aloop\nsnd-dummy\n' | sudo tee /etc/modules-load.d/virtual-audio.conf
   sudo tee /etc/modprobe.d/virtual-audio.conf >/dev/null <<'EOF'
   options snd-aloop enable=1,1,1,1,1,1,1,1 index=10
   options snd-dummy enable=1,1,1 index=11
   EOF
   ```
   Reload once (`modprobe -r snd-dummy snd-aloop` then modprobe again) so the running state
   matches the boot state. `cat /proc/asound/cards` must list `Loopback` and `Dummy`.
2. Let PipeWire pick up the cards (WirePlumber usually auto-detects within seconds; else
   `systemctl --user restart pipewire wireplumber`). **Restarting pipewire kills running ffmpeg
   recorders and rebuilds `auto_null`** — restart those services afterwards.
3. Create the userspace layer (idempotent script, e.g. `/home/ubuntu/ops/scripts/virtual-audio/setup-virtual-audio.sh`):
   * `module-null-sink sink_name=auto_null` → default sink, `auto_null.monitor` = system audio
   * `module-null-sink sink_name=VirtualMicSink` → injection target
   * `module-remap-source master=VirtualMicSink.monitor source_name=VirtualMic` → the microphone
   * `pactl set-default-sink auto_null`, `pactl set-default-source VirtualMic`
4. Persist as a systemd **user** unit ordered after pipewire:
   ```ini
   [Unit]
   After=pipewire.service pipewire-pulse.service wireplumber.service
   [Service]
   Type=oneshot
   RemainAfterExit=yes
   ExecStart=/home/ubuntu/ops/scripts/virtual-audio/setup-virtual-audio.sh
   [Install]
   WantedBy=default.target
   ```
   `systemctl --user enable --now virtual-audio.service` (keep the script idempotent: check with
   `pactl list short sinks|sources` before loading a module again).
5. Inject audio helper: `mic-play <file>` = `paplay --device=VirtualMicSink` (never `ffmpeg -f pulse <name>`, see Pitfalls);
   `mic-play --say "text"` = edge-tts → mic. Start it detached with
   `systemd-run --user --collect --unit=micplay <cmd>` — never shell `&`.

## Verify (do not skip)
```bash
systemd-run --user --collect --unit=micprobe .../mic-play --tone
sleep 2
timeout 8 parec --device=VirtualMic --rate=16000 --channels=1 --format=s16le > /tmp/vmic.raw
ffmpeg -hide_banner -f s16le -ar 16000 -ac 1 -i /tmp/vmic.raw -af volumedetect -f null - 2>&1 | grep volume
```
Expected `mean_volume ≈ -20..-10 dB`, `max_volume > -6 dB`. `-91 dB` means the injection path
or the device name is wrong.

Browser check (CDP): on a **secure context** page (`file://`, `https://`, `http://localhost`)
`navigator.mediaDevices.enumerateDevices()` must list an `audioinput` (e.g. `VirtualMicrophone`)
and `getUserMedia({audio:true})` must return a live track. Chrome flags that help:
`--use-fake-ui-for-media-stream` (auto-grant permission), `--autoplay-policy=no-user-gesture-required`.

## Pitfalls
* **`ffmpeg -f pulse <sink-name>` silently writes to the DEFAULT sink** — the named device is ignored,
  so injected TTS never reaches the mic and a capture of the mic reads `-91 dB` while the audio
  quietly plays out of the default sink. Use `paplay --device=<sink>` (or `PULSE_SINK=<sink>`).
* **Stray feeders fake success**: an orphan `pacat -d VirtualMicSink` kept hiss flowing into the mic
  and produced a plausible `-13 dB` "mic works" reading. Run `pactl list short sink-inputs` and
  `pgrep -af 'pacat|ffmpeg'` before trusting any mic/recording level test.
* **Chrome flags only apply to a NEW process**: `--autoplay-policy=no-user-gesture-required` +
  `--use-fake-ui-for-media-stream` let a meeting tab play audio and grab the mic without a click,
  but a running Chrome ignores them — restart the browser service between meetings.
* Recording browser/system audio needs the app output to land in the sink you record
  (`pactl set-default-sink auto_null`) and the meeting joined with **computer audio**; healthy
  capture is ≈ -25 dB, `-91 dB` means nothing is playing into the recorded sink.
* `about:blank` has no `navigator.mediaDevices` — use `file:///tmp/x.html` for quick tests.
* Chrome caches the default output device per stream; a running instance may keep the old device
  until the page creates a new stream (often needs a browser restart).
* A sink monitor is silent unless something **actively plays** into the sink; an idle attached
  stream is not evidence of audio.
* `snd-aloop` playback→capture is not a straight loopback across the exposed PipeWire nodes;
  use the null-sink + remap-source path instead of assuming ALSA loopback routing.
* Do not put `--use-fake-device-for-media-stream` in a production Chrome launch — it replaces real
  devices with a synthetic one and would defeat the virtual mic.
* On low-core VMs don't run whisper transcription alongside browser capture at full load.
