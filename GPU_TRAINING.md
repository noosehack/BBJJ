# GPU Training Handoff — g4dn.xlarge spot

## Current server info
- Region: eu-west-2
- VPC: vpc-0937cd3f60afc7089
- Subnet: subnet-0e70b254b36f4552d
- Security group: sg-047ee2ffb80d1fd41
- This server IP: 172.31.24.112
- SSH key: noosehack@protonmail.com (ed25519)

## 1. Launch GPU spot instance

From AWS Console (eu-west-2):

- AMI: **Deep Learning AMI (Ubuntu 22.04)** — comes with CUDA, PyTorch, drivers preinstalled
  - Search: `Deep Learning AMI GPU PyTorch` in Community AMIs
  - Or use Ubuntu 22.04 and install manually (step 3 below)
- Instance type: **g4dn.xlarge** (T4 16GB, 4 vCPU, 16GB RAM, ~$0.16/hr spot)
- Request spot instance (check "Request Spot Instances")
- Key pair: use your existing key or create one
- VPC/Subnet/SG: same as above (so the two instances can talk via private IP)
- Storage: **50 GB** gp3 (images are 9.7GB, model + workspace needs room)

Or via CLI (install `awscli` first: `pip install awscli && aws configure`):

```bash
aws ec2 run-instances \
  --image-id ami-0xxxx  \
  --instance-type g4dn.xlarge \
  --key-name YOUR_KEY \
  --instance-market-options '{"MarketType":"spot","SpotOptions":{"SpotInstanceType":"persistent","InstanceInterruptionBehavior":"stop"}}' \
  --subnet-id subnet-0e70b254b36f4552d \
  --security-group-ids sg-047ee2ffb80d1fd41 \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":50,"VolumeType":"gp3"}}]' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=bjj-pose-training}]' \
  --region eu-west-2
```

## 2. Copy data to GPU instance

From THIS server (172.31.24.112), rsync to the GPU instance over private network:

```bash
# Set GPU instance private IP
GPU=<gpu-instance-private-ip>

# Copy repo (code only, no data)
rsync -avz --exclude 'data/raw' --exclude 'data/yolo_pose' --exclude 'models_pose' \
  --exclude '__pycache__' --exclude '.git' \
  /home/ubuntu/BBJJ/ ubuntu@$GPU:/home/ubuntu/BBJJ/

# Copy exported YOLO dataset (50MB — small, fast)
rsync -avz /home/ubuntu/BBJJ/data/yolo_pose/ ubuntu@$GPU:/home/ubuntu/BBJJ/data/yolo_pose/

# Copy raw images (9.7GB — needed because yolo_pose symlinks point to them)
rsync -avz /home/ubuntu/BBJJ/data/raw/images/ ubuntu@$GPU:/home/ubuntu/BBJJ/data/raw/images/

# Copy annotations (for eval script)
rsync -avz /home/ubuntu/BBJJ/data/raw/annotations.json ubuntu@$GPU:/home/ubuntu/BBJJ/data/raw/annotations.json

# Copy base model
rsync -avz /home/ubuntu/BBJJ/yolo11m-pose.pt ubuntu@$GPU:/home/ubuntu/BBJJ/yolo11m-pose.pt 2>/dev/null || true
```

**Important:** The exported labels use symlinks to raw images. After rsync, fix them:

```bash
ssh ubuntu@$GPU 'cd /home/ubuntu/BBJJ && python3 -c "
import os
from pathlib import Path
for split in [\"train\", \"val\"]:
    img_dir = Path(f\"data/yolo_pose/{split}/images\")
    for f in img_dir.iterdir():
        if f.is_symlink():
            target = f.resolve()
            real = Path(\"data/raw/images\") / f.name
            if real.exists() and not target.exists():
                f.unlink()
                os.symlink(real.resolve(), f)
print(\"Symlinks fixed\")
"'
```

Or simpler — just re-export on the GPU box:
```bash
ssh ubuntu@$GPU 'cd /home/ubuntu/BBJJ && python3 -m tools.export_yolo_pose'
```

## 3. Install requirements on GPU instance

If using Deep Learning AMI, PyTorch+CUDA are already installed. Just add:

```bash
ssh ubuntu@$GPU 'pip install ultralytics pillow'
```

If using plain Ubuntu 22.04:
```bash
ssh ubuntu@$GPU 'pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121 && pip install ultralytics pillow'
```

Verify GPU is visible:
```bash
ssh ubuntu@$GPU 'python3 -c "import torch; print(f\"CUDA: {torch.cuda.is_available()}\"); print(f\"GPU: {torch.cuda.get_device_name(0)}\")"'
```

Expected: `CUDA: True` / `GPU: Tesla T4`

## 4. Train

### Strategy C: pose-head-only (recommended first run)

Freezes backbone + neck + detection head. Trains only keypoint branch (858K params).
Detection recall stays at baseline. Only keypoint placement adapts to grappling.

```bash
ssh ubuntu@$GPU 'cd /home/ubuntu/BBJJ && nohup python3 -m tools.train_pose \
  --epochs 50 \
  --imgsz 640 \
  --batch 32 \
  --pose-head-only \
  --name bjj_v2_posehead \
  > train.log 2>&1 &'
```

### Fallback — Strategy A: freeze backbone, train neck + full head

Use only if Strategy C fails to improve RAD accuracy.

```bash
ssh ubuntu@$GPU 'cd /home/ubuntu/BBJJ && nohup python3 -m tools.train_pose \
  --epochs 50 \
  --imgsz 640 \
  --batch 32 \
  --freeze 22 \
  --name bjj_v1_neck \
  > train.log 2>&1 &'
```

Monitor:
```bash
ssh ubuntu@$GPU 'tail -f /home/ubuntu/BBJJ/train.log'
```

Expected runtime: **2-4 hours** on T4 with 7.5K train images at 640px.

## 5. Copy back results

```bash
GPU=<gpu-instance-private-ip>

# Copy best model weights (Strategy C)
mkdir -p /home/ubuntu/BBJJ/models_pose/bjj_v2_posehead/weights
scp ubuntu@$GPU:/home/ubuntu/BBJJ/models_pose/bjj_v2_posehead/weights/best.pt \
  /home/ubuntu/BBJJ/models_pose/bjj_v2_posehead/weights/best.pt

# Copy training results/plots
rsync -avz ubuntu@$GPU:/home/ubuntu/BBJJ/models_pose/bjj_v2_posehead/ \
  /home/ubuntu/BBJJ/models_pose/bjj_v2_posehead/

# Copy training log
scp ubuntu@$GPU:/home/ubuntu/BBJJ/train.log /home/ubuntu/BBJJ/train.log
```

## 6. Evaluate (back on this server)

```bash
# Single model eval — pose-head-only
python3 -m tools.eval_pose_model --model models_pose/bjj_v2_posehead/weights/best.pt

# Compare baseline vs pose-head-only on test set (videos 08, 13, 15)
python3 -m tools.eval_pose_model --compare yolo11m-pose.pt models_pose/bjj_v2_posehead/weights/best.pt

# Quick inference test on a hard class image
python3 -m tools.infer_image some_mount_image.jpg --model models_pose/bjj_v2_posehead/weights/best.pt
```

Key metrics to check:
- Two-person detection rate must not regress vs baseline
- Hard classes (mount, side_control, back, closed_guard) reported separately
- RAD accuracy should improve over baseline

## 7. If spot is interrupted

YOLO saves checkpoints to `models_pose/bjj_v2_posehead/weights/last.pt` after every epoch.

To resume:
```bash
ssh ubuntu@$GPU 'cd /home/ubuntu/BBJJ && python3 -c "
from ultralytics import YOLO
model = YOLO(\"models_pose/bjj_v2_posehead/weights/last.pt\")
model.train(resume=True)
"'
```

If the instance was terminated (not just stopped), launch a new one, re-copy data, and resume from `last.pt` (copy it from this server if you already pulled it).

## 8. Cleanup

After copying results back, terminate the GPU instance to stop charges:

```bash
# From AWS Console or CLI
aws ec2 terminate-instances --instance-ids <instance-id> --region eu-west-2
```

Spot instances with `persistent` type need the spot request cancelled too:
```bash
aws ec2 cancel-spot-instance-requests --spot-instance-request-ids <sir-id> --region eu-west-2
```
