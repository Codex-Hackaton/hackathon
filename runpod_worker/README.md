# OFFMate RunPod VLM worker

The VLM extracts one activity candidate only. `policy.py` maps that extraction to
`PASS`, `FAIL`, or `HUMAN_REVIEW`, so the model cannot invent a penalty or unlock
action.

## Local policy tests

```bash
python3 -m unittest discover -s tests -v
```

## Container build

RunPod uses `linux/amd64`, including when the image is built on an Apple Silicon Mac.

```bash
docker build --platform linux/amd64 -t YOUR_REGISTRY/offmate-vlm:0.1 .
docker push YOUR_REGISTRY/offmate-vlm:0.1
```

Create a queue-based Serverless endpoint from the image and mount model cache storage
at `/runpod-volume`. The backend calls:

```text
POST https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync?wait=120000
```

Configure the backend without committing secrets:

```bash
export RUNPOD_ENDPOINT_ID="..."
export RUNPOD_API_KEY="..."
```
