# Dependency and ESP-IDF compatibility validation

The dependency proposal is based on SDK v0.3.11. It retains esp_peer 1.5.5
and WebSocket 1.8.0 and pins capture to 1.0.2. It adds no S31-specific code.

## Validation on 2026-09-20

The combined dependency, generic-fix and S31-support candidate passed all
seven S31 example builds on ESP-IDF 6.1 with the documented S31 toolchain
patch. Every image fits its existing application partition. All 238 managed
component instances passed checksum verification.

That combined candidate also passed attended voice and board-control checks
on Korvo-1 and Function-CoreBoard-1, audio recovery after an agent restart
on Korvo-1, and the existing sustained Korvo camera/audio receiver test.
The latter received 6,294 video frames and 62,999 audio frames over
628.216 seconds of video, with a maximum video gap of 362 milliseconds.

These results exercise this dependency set with the other proposed changes;
they are not standalone S3/P4 verification. The standalone ESP-IDF
5.4.4/5.5.3 S3/P4 CI matrix and registry dry-run action have not been rerun.
Previous CI results retain their original dependency versions and scope.
