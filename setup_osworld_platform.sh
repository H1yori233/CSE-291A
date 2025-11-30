#!/bin/bash

# Configuration Variables
# -----------------------
AWS_REGION="us-east-1"           # Default region from the guide
KEY_NAME="osworld-host-key"      # REPLACE with your actual key pair name in AWS
INSTANCE_TYPE="t3.medium"        # UPDATED: Sufficient for <5 parallel envs
HOST_SG_NAME="OSWorld-Host-SG"
CLIENT_SG_NAME="OSWorld-Client-SG"
AMI_NAME_FILTER="ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*" # Ubuntu 24.04 LTS

# 1. Get Default VPC and Subnet
# -----------------------------
echo "Fetching Default VPC..."
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text --region $AWS_REGION)
SUBNET_ID=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[0].SubnetId" --output text --region $AWS_REGION)
CIDR_BLOCK=$(aws ec2 describe-vpcs --vpc-ids $VPC_ID --query "Vpcs[0].CidrBlock" --output text --region $AWS_REGION)

echo "Using VPC: $VPC_ID ($CIDR_BLOCK)"
echo "Using Subnet: $SUBNET_ID"

# 2. Create Host Security Group (Section 1.1)
# -------------------------------------------
echo "Creating Host Security Group..."
HOST_SG_ID=$(aws ec2 create-security-group --group-name $HOST_SG_NAME --description "SG for OSWorld Host" --vpc-id $VPC_ID --output text --region $AWS_REGION 2>/dev/null || aws ec2 describe-security-groups --filters "Name=group-name,Values=$HOST_SG_NAME" --query "SecurityGroups[0].GroupId" --output text --region $AWS_REGION)

# Allow SSH (22) and Monitor (8080) from Anywhere
aws ec2 authorize-security-group-ingress --group-id $HOST_SG_ID --protocol tcp --port 22 --cidr 0.0.0.0/0 --region $AWS_REGION 2>/dev/null
aws ec2 authorize-security-group-ingress --group-id $HOST_SG_ID --protocol tcp --port 8080 --cidr 0.0.0.0/0 --region $AWS_REGION 2>/dev/null

# 3. Create Client Security Group (Section 1.3 Step 1)
# ----------------------------------------------------
echo "Creating Client Security Group..."
CLIENT_SG_ID=$(aws ec2 create-security-group --group-name $CLIENT_SG_NAME --description "SG for OSWorld Clients" --vpc-id $VPC_ID --output text --region $AWS_REGION 2>/dev/null || aws ec2 describe-security-groups --filters "Name=group-name,Values=$CLIENT_SG_NAME" --query "SecurityGroups[0].GroupId" --output text --region $AWS_REGION)

# Define Inbound Rules from the Table in Section 1.3
# Rules for 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $CLIENT_SG_ID --protocol tcp --port 22 --cidr 0.0.0.0/0 --region $AWS_REGION 2>/dev/null
aws ec2 authorize-security-group-ingress --group-id $CLIENT_SG_ID --protocol tcp --port 5910 --cidr 0.0.0.0/0 --region $AWS_REGION 2>/dev/null

# Rules for Internal VPC Traffic (HTTP, Backend, VNC services)
aws ec2 authorize-security-group-ingress --group-id $CLIENT_SG_ID --protocol tcp --port 80 --cidr $CIDR_BLOCK --region $AWS_REGION 2>/dev/null
aws ec2 authorize-security-group-ingress --group-id $CLIENT_SG_ID --protocol tcp --port 5000 --cidr $CIDR_BLOCK --region $AWS_REGION 2>/dev/null
aws ec2 authorize-security-group-ingress --group-id $CLIENT_SG_ID --protocol tcp --port 8006 --cidr $CIDR_BLOCK --region $AWS_REGION 2>/dev/null
aws ec2 authorize-security-group-ingress --group-id $CLIENT_SG_ID --protocol tcp --port 8080 --cidr $CIDR_BLOCK --region $AWS_REGION 2>/dev/null
aws ec2 authorize-security-group-ingress --group-id $CLIENT_SG_ID --protocol tcp --port 8081 --cidr $CIDR_BLOCK --region $AWS_REGION 2>/dev/null
aws ec2 authorize-security-group-ingress --group-id $CLIENT_SG_ID --protocol tcp --port 9222 --cidr $CIDR_BLOCK --region $AWS_REGION 2>/dev/null

echo "Host SG ID: $HOST_SG_ID"
echo "Client SG ID: $CLIENT_SG_ID"

# 4. Get Latest Ubuntu AMI
# ------------------------
echo "Fetching latest Ubuntu 24.04 AMI..."
AMI_ID=$(aws ec2 describe-images --owners 099720109477 --filters "Name=name,Values=$AMI_NAME_FILTER" "Name=state,Values=available" --query "sort_by(Images, &CreationDate)[-1].ImageId" --output text --region $AWS_REGION)
echo "Using AMI: $AMI_ID"

# 5. Prepare User Data Script (Runs on Host First Boot)
# -----------------------------------------------------
# This automates Section 1.2 Step 3 (Environment Setup)
cat <<EOF > user_data_script.sh
#!/bin/bash
# System Updates
apt-get update -y
apt-get upgrade -y
apt-get install -y git python3-pip python3-venv

# Clone Repository
cd /home/ubuntu
sudo -u ubuntu git clone https://github.com/xlang-ai/OSWorld.git
cd OSWorld

# Setup Python Environment
sudo -u ubuntu python3 -m venv osworld_env
source osworld_env/bin/activate

# Install Dependencies
sudo -u ubuntu ./osworld_env/bin/pip install -r requirements.txt

# Create a file with environment vars for easier setup later
cat <<EOT >> /home/ubuntu/osworld_env_vars.sh
export AWS_REGION=$AWS_REGION
export AWS_SECURITY_GROUP_ID=$CLIENT_SG_ID
export AWS_SUBNET_ID=$SUBNET_ID
EOT
chown ubuntu:ubuntu /home/ubuntu/osworld_env_vars.sh

EOF

# 6. Launch Host Instance
# -----------------------
echo "Launching Host Instance ($INSTANCE_TYPE)..."
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $AMI_ID \
    --count 1 \
    --instance-type $INSTANCE_TYPE \
    --key-name $KEY_NAME \
    --security-group-ids $HOST_SG_ID \
    --subnet-id $SUBNET_ID \
    --block-device-mappings "[{\"DeviceName\":\"/dev/sda1\",\"Ebs\":{\"VolumeSize\":50,\"VolumeType\":\"gp3\"}}]" \
    --user-data file://user_data_script.sh \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=OSWorld-Host}]' \
    --query "Instances[0].InstanceId" \
    --output text \
    --region $AWS_REGION)

echo "Instance $INSTANCE_ID launching..."
echo "Waiting for instance to be running..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $AWS_REGION

PUBLIC_DNS=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query "Reservations[0].Instances[0].PublicDnsName" --output text --region $AWS_REGION)

# 7. Final Instructions
# ---------------------
echo "=========================================================="
echo "Deployment Complete!"
echo "Host Public DNS: $PUBLIC_DNS"
echo "Client Security Group ID: $CLIENT_SG_ID"
echo "Subnet ID: $SUBNET_ID"
echo ""
echo "NEXT STEPS:"
echo "1. Connect to your host:"
echo "   ssh -i /path/to/$KEY_NAME.pem ubuntu@$PUBLIC_DNS"
echo ""
echo "2. Once logged in, load the configured variables:"
echo "   source ~/osworld_env_vars.sh"
echo "   export AWS_ACCESS_KEY_ID='YOUR_KEY'"
echo "   export AWS_SECRET_ACCESS_KEY='YOUR_SECRET'"
echo ""
echo "3. Activate the environment (created automatically, may require re-install due to some problem with numpy):"
echo "   cd ~/OSWorld"
echo "   source osworld_env/bin/activate"
echo "=========================================================="

rm user_data_script.sh