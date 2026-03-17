param(
    [string]$KubeconfigPath = ".\\linode-kubeconfig.yaml"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$taskRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$resolvedKubeconfig = (Resolve-Path $KubeconfigPath).Path
$env:KUBECONFIG = $resolvedKubeconfig

kubectl apply -f (Join-Path $taskRoot "k8s\\deployment.yaml")
kubectl apply -f (Join-Path $taskRoot "k8s\\service-loadbalancer.yaml")
kubectl get deployment web-server
kubectl get svc web-server-service -o wide
