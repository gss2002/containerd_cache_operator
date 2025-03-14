# containerd_cache_operator for configuring Pull Through Cache and updating the sandbox_image for Containerd using Kubernetes DaemonSets
Note: The idea for this came from the "NVIDIA Container Toolkit" and how it configures containerd settings across GPU Nodes https://github.com/NVIDIA/nvidia-container-toolkit

The sandbox_image option came from this error:

W0301 14:50:53.754779 3779932 checks.go:846] detected that the sandbox image "registry.k8s.io/pause:3.8" of the container runtime is inconsistent with that used by kubeadm.It is recommended to use "registry.k8s.io/pause:3.10" as the CRI sandbox image.


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
