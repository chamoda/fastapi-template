# Nginx Ingress Controller Setup for OKE

## Overview
This setup uses Nginx Ingress Controller to handle subdomain routing for multiple instances. A single OCI Load Balancer will be created automatically.

## Prerequisites
- Oracle Kubernetes Engine cluster
- kubectl configured
- Helm 3 installed
- DNS control for your domain

## Installation Steps

### 1. Install Nginx Ingress Controller
```bash
# Run the installation script
./scripts/install-nginx-ingress.sh
```

This will:
- Deploy Nginx Ingress Controller
- Create an OCI Load Balancer (Flexible shape, 10Mbps)
- Output the Load Balancer IP

### 2. Configure DNS
Add a wildcard A record to your DNS:
```
*.almastack.site → <LOAD_BALANCER_IP>
```

### 3. Deploy Instances
```bash
# Deploy an instance
uv run python manage.py k8s-deploy test123

# Access it at
http://test123.almastack.site
```

## How It Works
1. Each instance gets its own:
   - Namespace: `hello-<instance-id>`
   - Deployment, Service, ConfigMap
   - Ingress rule for subdomain routing

2. Traffic flow:
   - User → DNS → OCI Load Balancer → Nginx Ingress → Service → Pod

3. The Nginx Ingress Controller:
   - Watches all Ingress resources
   - Configures routing based on host rules
   - Single Load Balancer for all instances

## Cost Considerations
- OCI Load Balancer: ~$15/month (Flexible 10Mbps)
- Can handle hundreds of instances
- More cost-effective than Load Balancer per instance

## Troubleshooting

### Check Ingress Controller Status
```bash
kubectl get pods -n ingress-nginx
kubectl get svc -n ingress-nginx
```

### Check Ingress Rules
```bash
kubectl get ingress -A
```

### View Nginx Configuration
```bash
kubectl exec -n ingress-nginx deployment/nginx-ingress-ingress-nginx-controller -- cat /etc/nginx/nginx.conf
```
