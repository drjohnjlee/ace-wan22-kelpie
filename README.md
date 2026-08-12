# ACE Wan 2.2 Salad worker

This worker fixes the startup behavior of Salad's original Wan 2.2 Kelpie recipe.
Kelpie starts immediately, claims the queued job, and then the claimed job downloads
or resumes `Wan-AI/Wan2.2-TI2V-5B`. Model transfer time is therefore visible in the
job state instead of looking like an idle worker.

## Runtime flow

1. `/opt/entrypoint.sh` launches Kelpie immediately.
2. A job runs `python /opt/run_wan_job.py` with the normal Wan arguments.
3. `run_wan_job.py` downloads or resumes the model in `/opt/models`.
4. `wan_worker.py` renders to `/opt/outputs`.
5. Kelpie uploads `/opt/outputs` through the job's `sync.after` rule.

The model is intentionally not baked into the image. Wan's weights are large enough
to make the image slow to distribute and risk Salad's compressed-image size limit.

## Build

From this directory:

```bash
docker build -t REGISTRY/ace-wan22-kelpie:0.1.0 .
docker push REGISTRY/ace-wan22-kelpie:0.1.0
```

The current project has no configured container registry or Git remote. Choose a
private registry or a public image repository before running the publish step.

## Salad configuration

- Replicas: `1`
- GPU: `RTX 5090`, exactly `1`
- Priority: `High`
- CPU: `16 vCPU`
- Memory: `30 GB`
- Storage: `250 GB`
- Container image: the immutable tag produced above
- Environment: storage credentials should be entered only in Salad's secret UI

Salad automatically injects its organization, project, container-group, and machine
identity variables. Do not put the Salad API key, R2 secret, or Hugging Face token in
this directory.

## Kelpie job command

Use this command in the job definition:

```text
python /opt/run_wan_job.py --id CLIP_ID --prompt PROMPT --image-path /opt/assets/REFERENCE.png --frame-num 81 --sample-steps 30 --output-filename CLIP_ID
```

For a 16 fps export, 81 frames is about 5.1 seconds. The image and output paths should
be covered by the job's `sync.before` and `sync.after` rules respectively.
