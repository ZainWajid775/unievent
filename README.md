# UniEvent — Scalable University Event Management System on AWS
### CE 308/408 Cloud Computing Assignment — GIKI

A cloud-native web application that fetches live events from the Ticketmaster API and displays them as university events. Built on AWS using EC2, S3, ELB, VPC, and IAM, deployed with Terraform and CI/CD via GitHub Actions.

---

## Architecture Overview

```
Internet
    │
    ▼
[Application Load Balancer]  ← Public Subnets (AZ-1, AZ-2)
    │
    ├──────────────────────────┐
    ▼                          ▼
[EC2 Instance 1]          [EC2 Instance 2]   ← Private Subnets (AZ-1, AZ-2)
 Flask + Gunicorn           Flask + Gunicorn
    │                          │
    └──────────┬───────────────┘
               │
               ▼
          [NAT Gateway]  →  Ticketmaster API (outbound)
               │
          [S3 Bucket]
          ├── events/latest_events.json
          └── posters/...

IAM Role on EC2 → scoped S3 read/write only
```

**Services used:**
| Service | Purpose |
|---------|---------|
| **VPC** | Isolated network with public + private subnets across 2 AZs |
| **EC2** | Flask app instances in private subnets (Auto Scaling Group) |
| **ALB** | Distributes HTTP traffic across EC2 instances |
| **S3** | Stores event JSON data and uploaded posters (encrypted, private) |
| **IAM** | EC2 instance role with least-privilege S3 access |
| **NAT Gateway** | Allows private-subnet EC2s to call the Ticketmaster API |

---

## Prerequisites

Install these tools before starting:

| Tool | Install |
|------|---------|
| AWS CLI v2 | https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html |
| Terraform ≥ 1.6 | https://developer.hashicorp.com/terraform/downloads |
| Python 3.12 | https://www.python.org/downloads/ |
| Git | https://git-scm.com/downloads |

---

## Step 1 — Get a Free Ticketmaster API Key

1. Go to https://developer.ticketmaster.com/
2. Click **"Get Your API Key"** → create a free account
3. Create a new App — you'll receive a **Consumer Key** (this is your API key)
4. Keep it handy — you'll add it to your `.tfvars` and GitHub Secrets

> The app works without a key too — it falls back to mock university events automatically.

---

## Step 2 — Configure AWS CLI

```bash
aws configure
# Enter your:
#   AWS Access Key ID
#   AWS Secret Access Key
#   Default region: us-east-1
#   Output format: json
```

To get AWS credentials:
- Log into AWS Console → IAM → Users → your user → Security Credentials → Create Access Key

---

mkdir -p ~/.ssh
```

On Windows, open **Command Prompt or PowerShell** and run:
```
mkdir %USERPROFILE%\.ssh

## Step 4 — Push This Repo to GitHub

```bash
# 1. Create a new EMPTY repo on github.com (no README, no .gitignore)
# 2. Then in your terminal:

cd unievent
git init
git add .
git commit -m "Initial commit: UniEvent AWS deployment"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/unievent.git
git push -u origin main
```

---

## Step 5 — Add GitHub Secrets

In your GitHub repo → **Settings → Secrets and Variables → Actions** → New repository secret:

| Secret Name | Value |
|-------------|-------|
| `AWS_ACCESS_KEY_ID` | Your AWS access key |
| `AWS_SECRET_ACCESS_KEY` | Your AWS secret key |
| `TICKETMASTER_API_KEY` | Your Ticketmaster API key |

---

## Step 6 — Update user_data.sh with Your Repo URL

Open `terraform/user_data.sh` and replace:
```bash
git clone https://github.com/YOUR_USERNAME/unievent.git
```
with your actual GitHub repo URL. Then commit and push:

```bash
git add terraform/user_data.sh
git commit -m "Set GitHub repo URL in user_data"
git push
```

---

## Step 7 — Configure Terraform Variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
```hcl
aws_region           = "us-east-1"
project_name         = "unievent"
s3_bucket_name       = "unievent-media-bucket-giki-2025"  # change to something unique
instance_type        = "t3.micro"
key_pair_name        = "unievent-key"
ssh_allowed_cidr     = "0.0.0.0/0"
ticketmaster_api_key = "YOUR_TICKETMASTER_API_KEY"
```

> ⚠️ S3 bucket names must be **globally unique**. Add your name or student ID to make it unique.

---

## Step 8 — Deploy with Terraform

```bash
cd terraform

# Initialize Terraform (downloads AWS provider)
terraform init

# Preview what will be created
terraform plan

# Deploy everything (~5 minutes)
terraform apply
# Type 'yes' when prompted
```

At the end you'll see:
```
Outputs:
app_url = "http://unievent-alb-XXXXXXXX.us-east-1.elb.amazonaws.com"
```

Open that URL in your browser — **your app is live!**

---

## Step 9 — Run Locally (for development/testing)

```bash
cd app
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

export S3_BUCKET="unievent-media-bucket-giki-2025"
export AWS_REGION="us-east-1"
export TICKETMASTER_API_KEY="your_key_here"

python app.py
# Open http://localhost:5000
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main events page (HTML) |
| `/api/events` | GET | Returns events as JSON |
| `/api/events/refresh` | POST | Triggers immediate API fetch + S3 save |
| `/api/upload-poster` | POST | Upload an image to S3 (multipart/form-data) |
| `/health` | GET | Health check (used by ALB) |

---

## Project Structure

```
unievent/
├── app/
│   ├── app.py                 # Flask application
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile             # Container definition
│   └── templates/
│       └── index.html         # Frontend UI
├── terraform/
│   ├── main.tf                # VPC, subnets, IGW, NAT
│   ├── resources.tf           # SG, IAM, S3, EC2, ALB
│   ├── variables.tf           # Input variables
│   ├── outputs.tf             # Output values
│   ├── user_data.sh           # EC2 bootstrap script
│   └── terraform.tfvars.example
├── .github/
│   └── workflows/
│       └── deploy.yml         # CI/CD pipeline
├── .gitignore
└── README.md
```

---

## Teardown (avoid AWS charges)

```bash
cd terraform
terraform destroy
# Type 'yes' when prompted
```

This deletes all AWS resources created by Terraform.

---

## Security Design Decisions

1. **EC2 in private subnets** — instances are not directly reachable from the internet; only the ALB is public-facing
2. **IAM least privilege** — EC2 role only has `s3:GetObject`, `s3:PutObject`, `s3:ListBucket` on the specific bucket
3. **S3 block public access** — all bucket objects are private; posters are served via presigned URLs
4. **S3 server-side encryption** — AES-256 encryption at rest
5. **Security groups** — EC2 SG only allows port 5000 from the ALB SG; no direct internet access
6. **NAT Gateway** — EC2 instances reach the Ticketmaster API outbound but cannot be reached inbound
7. **No hardcoded secrets** — API keys are passed via environment variables and GitHub Secrets

---

## Fault Tolerance

- Auto Scaling Group runs **minimum 2 EC2 instances** across 2 Availability Zones
- ALB health checks on `/health` — automatically routes away from unhealthy instances
- If one instance fails, ASG launches a replacement within 2 minutes
- Event data is cached in S3, so the app can serve events even if the external API is down
