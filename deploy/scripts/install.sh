#!/bin/bash
# ProTech NAS — System Dependencies Installation Script
# Supports: Debian 12 / Ubuntu Server 22.04+
set -e

echo "=== ProTech NAS — Installing System Dependencies ==="

# Update package lists
sudo apt update

# Install core packages
sudo apt install -y \
    samba \
    nfs-kernel-server \
    docker.io \
    docker-compose \
    python3 \
    python3-venv \
    python3-pip \
    smartmontools \
    mdadm \
    curl \
    wget

# Install optional packages for full functionality
sudo apt install -y \
    exfatprogs \
    lm-sensors \
    traceroute \
    dnsutils \
    nginx

# Install Node.js 20.x (via NodeSource)
if ! command -v node &> /dev/null; then
    echo "Installing Node.js 20.x..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt install -y nodejs
fi

# Enable and start services
sudo systemctl enable docker
sudo systemctl start docker
sudo systemctl enable smbd
sudo systemctl start smbd
sudo systemctl enable nfs-kernel-server
sudo systemctl start nfs-kernel-server

# Add current user to docker group
sudo usermod -aG docker $USER

echo ""
echo "=== Installation Complete ==="
echo "Node.js: $(node --version)"
echo "Python:  $(python3 --version)"
echo "Docker:  $(docker --version)"
echo ""
echo "Next: Run ./scripts/setup_deps.sh to install project dependencies."
echo "Note: Log out and back in for docker group to take effect."
