FROM pytorch/pytorch:2.7.0-cuda12.8-cudnn9-devel

ARG WAN_REPOSITORY=https://github.com/Wan-Video/Wan2.2.git
ARG WAN_REF=main
ARG KELPIE_VERSION=0.7.2

ENV DEBIAN_FRONTEND=noninteractive \
    CUDA_HOME=/usr/local/cuda \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    HF_HUB_ENABLE_HF_TRANSFER=1 \
    TORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

ENV PATH=${CUDA_HOME}/bin:${PATH}

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        ffmpeg \
        git \
        tini && \
    rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade --no-cache-dir pip wheel packaging setuptools

WORKDIR /opt
RUN git clone --filter=blob:none "${WAN_REPOSITORY}" Wan2.2 && \
    cd Wan2.2 && \
    git checkout "${WAN_REF}" && \
    sed -i '/^[[:space:]]*flash_attn[[:space:]]*$/d' requirements.txt && \
    python -m pip install --no-cache-dir -r requirements.txt

# Flash Attention is optional; build it where the base PyTorch is visible.
RUN python -m pip install --no-cache-dir flash-attn --no-build-isolation || true

RUN python -m pip install --no-cache-dir \
        "huggingface_hub[cli]" \
        hf_transfer \
        requests \
        azure-storage-blob \
        azure-identity \
        av \
        moviepy \
        librosa \
        decord \
        timm

RUN curl -fsSL --retry 5 --retry-connrefused --connect-timeout 30 --http1.1 \
        -o /usr/local/bin/kelpie \
        "https://github.com/SaladTechnologies/kelpie/releases/download/${KELPIE_VERSION}/kelpie" && \
    chmod 0755 /usr/local/bin/kelpie && \
    ln -s /usr/local/bin/kelpie /kelpie

COPY entrypoint.sh /opt/entrypoint.sh
COPY run_wan_job.py /opt/run_wan_job.py
COPY wan_worker.py /opt/wan_worker.py

RUN chmod 0755 /opt/entrypoint.sh /opt/run_wan_job.py /opt/wan_worker.py && \
    mkdir -p /opt/checkpoints /opt/outputs /opt/assets /opt/models

WORKDIR /opt
ENTRYPOINT ["/usr/bin/tini", "--", "/opt/entrypoint.sh"]
CMD []
