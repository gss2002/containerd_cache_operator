# containerd_cache_operator for configuring Pull Through Cache and updating the sandbox_image for Containerd using Kubernetes DaemonSets
Note: The idea for this came from the "NVIDIA Container Toolkit" and how it configures containerd settings across GPU Nodes https://github.com/NVIDIA/nvidia-container-toolkit

You can use a tool such as this to create local container registry pull through cache - https://github.com/obeone/multi-registry-cache

## Build Docker Container Image to Manage containerd Pull Through Cache
docker build -t containerd-cache:latest .

docker tag containerd-cache:latest registry.devops.example.org/k8s/images/containerd-cache:latest

docker push registry.devops.example.org/k8s/images/containerd-cache:latest

## Apply K8S Manifests
#### Apply Containerd Config Map:
kubectl apply -f containerd-cm.yaml 
#### Apply containerd_cache_operator daemonset to configure containerd pull through cache across all nodes in a K8S/EKS Cluster
kubectl apply -f ds.yaml 
