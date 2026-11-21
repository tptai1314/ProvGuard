# EC2 experiment guide

> **EC2 is not a hard requirement.** It is a stand-in for any Linux host with enough disk and
> RAM to build AOSP (a lab server or a Linux workstation works). The userspace prototype
> (Track A) runs entirely on a local machine with an Android emulator; only the AOSP track
> needs Linux.

This repository does not download data, clone agent repositories, build AOSP, start devices,
or invoke model APIs automatically.

1. Choose an EC2 instance and attached storage suitable for the pinned AOSP release and
   models. Install Android build prerequisites yourself.
2. Manually obtain AOSP, apply reviewed patches from `aosp/patches/`, and record patch
   hashes and the build fingerprint. Flash only authorized Pixel devices or prepare the
   benchmark emulator image.
3. Manually obtain the four agent repositories and checkpoints. Replace every `TODO_PIN_*`
   in `configs/experiment_template.yaml` with real versions.
4. Manually obtain each benchmark after satisfying its license, registration, and/or
   authentication requirements. Normalize outcomes to `docs/data_format.md` under
   `<data.root>/trials.jsonl`.
5. Verify normalized data without running a model:

   ```bash
   python -m provguard.cli validate-data --root /mnt/provguard-data/normalized
   ```

6. Run the externally implemented AOSP/agent harness. It must emit one normalized record
   per trial and preserve raw logs.
7. Point `data.root` to those already-generated logs and compute metrics:

   ```bash
   python scripts/run_experiment.py --config configs/experiment_template.yaml --stage evaluate
   python scripts/make_plots.py --input outputs/real_run/results.json --output outputs/real_run
   ```

8. Update `audits/result_integrity_audit.md` with the exact provenance before treating any
   output as a real result.

The harness for steps 2 and 6 cannot be completed from the manuscript alone: concrete
AOSP method signatures, patch base, device model, agent commits, model checkpoints,
credentials, and several artifacts are manuscript placeholders.

