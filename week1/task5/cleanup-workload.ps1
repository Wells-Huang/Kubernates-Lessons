param(
    [string]$KubeconfigPath = ".\\linode-kubeconfig.yaml"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$taskRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$resolvedKubeconfig = (Resolve-Path $KubeconfigPath).Path
$env:KUBECONFIG = $resolvedKubeconfig

kubectl delete -f (Join-Path $taskRoot "k8s\\service-loadbalancer.yaml") --ignore-not-found=true
kubectl delete -f (Join-Path $taskRoot "k8s\\deployment.yaml") --ignore-not-found=true
