# Week1 Task5

這份 `README.md` 使用 UTF-8 編碼。

## 題目需求確認

這題要完成以下事項：

1. 建立一個雲端 Kubernetes Cluster。
2. 建立方式要可重複執行，並且方便 cleanup。
3. 把建立步驟與設定檔留存在 repo。
4. 在該 Cluster 中部署 `task1` 的 Nginx 資源，但把 Service 改成 `LoadBalancer`。
5. 確認雲端 Load Balancer 已成功建立，並透過它存取 Nginx 頁面。

## 本次實作方案

- 雲端平台：Linode LKE
- IaC 工具：Terraform
- Terraform 執行位置：WSL
- Kubernetes 操作工具：Windows `kubectl`

這個方案符合題目要求，因為：

- 建立 Cluster：`terraform apply`
- 銷毀 Cluster：`terraform destroy`
- 工作負載部署：`apply-workload.ps1`
- 工作負載清理：`cleanup-workload.ps1`

## 目錄結構

```text
week1/task5/
├─ terraform/
│  ├─ main.tf
│  ├─ outputs.tf
│  ├─ terraform.tfvars.example
│  ├─ variables.tf
│  └─ versions.tf
├─ k8s/
│  ├─ deployment.yaml
│  └─ service-loadbalancer.yaml
├─ apply-workload.ps1
├─ cleanup-workload.ps1
└─ README.md
```

以下檔案只會存在本機，不應推送到 Git：

- `terraform/terraform.tfvars`
- `terraform/terraform.tfstate`
- `terraform/terraform.tfstate.backup`
- `terraform/.terraform/`
- `terraform/.terraform.lock.hcl`
- `linode-kubeconfig.yaml`

## 環境確認結果

檢查日期：2026-03-17

- Windows 已安裝：`kubectl`、`docker`、`minikube`
- WSL 已安裝：`terraform v1.14.1`
- WSL 未安裝：`kubectl`
- Windows 本機的 `task1` Minikube 當時是停止狀態，但不影響本題，因為本題使用新的雲端 LKE Cluster

## Terraform 設定

實際使用的參數如下：

```hcl
cluster_label  = "week1-task5-lke"
region         = "us-central"
k8s_version    = "1.34"
node_pool_type = "g6-standard-2"
node_count     = 3
```

Linode Token 不寫入檔案，改用環境變數提供：

```bash
export TF_VAR_linode_token="YOUR_LINODE_TOKEN"
```

## 建立步驟

### Step 1. 進入 Terraform 目錄

```bash
cd /mnt/c/Users/Wells/Projects/Kubernates-Lessons/week1/task5/terraform
pwd
ls
```

應該會看到：

- `main.tf`
- `variables.tf`
- `outputs.tf`
- `versions.tf`
- `terraform.tfvars.example`

### Step 2. 初始化與建立 LKE Cluster

先用範例檔建立自己的本機參數檔：

```bash
cp terraform.tfvars.example terraform.tfvars
```

```bash
terraform init
terraform plan
terraform apply
```

建立完成後，再匯出 kubeconfig：

```bash
terraform output -raw kubeconfig | base64 -d > /mnt/c/Users/Wells/Projects/Kubernates-Lessons/week1/task5/linode-kubeconfig.yaml
```

### Step 3. 在 Windows 指定 kubeconfig

如果目前目錄是 `C:\Users\Wells\Projects\Kubernates-Lessons\week1\task5`，請使用：

```powershell
$env:KUBECONFIG = (Resolve-Path .\linode-kubeconfig.yaml).Path
kubectl get nodes -o wide
```

如果目前目錄是 repo 根目錄 `C:\Users\Wells\Projects\Kubernates-Lessons`，則使用：

```powershell
$env:KUBECONFIG = (Resolve-Path .\week1\task5\linode-kubeconfig.yaml).Path
kubectl get nodes -o wide
```

## 實際成功結果

### 1. 雲端節點已成功建立

2026-03-17 實際執行 `kubectl get nodes -o wide`，結果如下：

```text
NAME                            STATUS   ROLES    AGE   VERSION   INTERNAL-IP      EXTERNAL-IP      OS-IMAGE                         KERNEL-VERSION         CONTAINER-RUNTIME
lke<cluster-id>-<node-a>        Ready    <none>   21m   v1.34.3   <private-ip-a>   <public-ip-a>    Debian GNU/Linux 12 (bookworm)   6.1.0-41-cloud-amd64   containerd://2.2.1
lke<cluster-id>-<node-b>        Ready    <none>   21m   v1.34.3   <private-ip-b>   <public-ip-b>    Debian GNU/Linux 12 (bookworm)   6.1.0-41-cloud-amd64   containerd://2.2.1
lke<cluster-id>-<node-c>        Ready    <none>   21m   v1.34.3   <private-ip-c>   <public-ip-c>    Debian GNU/Linux 12 (bookworm)   6.1.0-41-cloud-amd64   containerd://2.2.1
```

### 2. 部署 task1 的 Nginx，但 Service 改成 LoadBalancer

在 `week1/task5/k8s` 中：

- `deployment.yaml`：沿用 task1 的 3 個 Nginx replicas
- `service-loadbalancer.yaml`：改用 `type: LoadBalancer`

部署指令：

```powershell
.\apply-workload.ps1 -KubeconfigPath .\linode-kubeconfig.yaml
kubectl get pods -o wide
kubectl get svc web-server-service -w
```

### 3. Load Balancer 已成功建立

實際觀察到：

```text
NAME                 TYPE           CLUSTER-IP       EXTERNAL-IP    PORT(S)        AGE
web-server-service   LoadBalancer   <cluster-ip>     <external-ip>  80:<nodeport>/TCP   33s
```

這代表 Linode 雲端 Load Balancer 已建立成功。

### 4. 已透過 Load Balancer 成功存取 Nginx 頁面

驗證指令：

```powershell
curl.exe http://<external-ip>
```

實際回應：

```html
<!DOCTYPE html>
<html>
<head>
<title>Welcome to nginx!</title>
<style>
    body {
        width: 35em;
        margin: 0 auto;
        font-family: Tahoma, Verdana, Arial, sans-serif;
    }
</style>
</head>
<body>
<h1>Welcome to nginx!</h1>
<p>If you see this page, the nginx web server is successfully installed and
working. Further configuration is required.</p>

<p>For online documentation and support please refer to
<a href="http://nginx.org/">nginx.org</a>.<br/>
Commercial support is available at
<a href="http://nginx.com/">nginx.com</a>.</p>

<p><em>Thank you for using nginx.</em></p>
</body>
</html>
```

### 5. 透過 Pod logs 驗證流量有進到後端

驗證指令：

```powershell
kubectl logs -l app=nginx --tail=20 --prefix=true
```

實際結果：

```text
[pod/web-server-<pod-id>/nginx] <source-ip> - - [17/Mar/2026:06:11:49 +0000] "GET / HTTP/1.1" 200 612 "-" "curl/8.18.0" "-"
```

這表示從 Load Balancer 進來的請求已經成功轉發到 Nginx Pod。

## 常見錯誤排查

如果你看到：

```text
Error: No configuration files
```

通常代表你執行 `terraform plan` 或 `terraform apply` 時，不在 `week1/task5/terraform` 目錄。

如果你看到：

```text
Error: Inconsistent dependency lock file
```

通常代表該目錄尚未正確執行 `terraform init`。

如果你看到：

```text
Error: No value for required variable
```

代表你尚未設定：

```bash
export TF_VAR_linode_token="YOUR_LINODE_TOKEN"
```

如果你看到：

```text
Error: failed to create LKE cluster: [401] Your OAuth token is not authorized to use this endpoint.
```

代表 token 已讀到，但權限不足。依 Linode 官方文件，至少要有以下 `Read/Write` 權限：

- `Compute Instances`
- `Kubernetes`
- `NodeBalancers`
- `Volumes`

如果你看到：

```text
Error: failed to create LKE cluster: [400] [k8s_version] k8s_version is not valid
```

代表指定的 Kubernetes 版本已不在 Linode 目前可建立 LKE 的版本清單中。本次改用 `1.34` 後成功建立。

## Cleanup

先刪除工作負載：

```powershell
.\cleanup-workload.ps1 -KubeconfigPath .\linode-kubeconfig.yaml
```

再回 WSL 刪除整個 Cluster：

```bash
cd /mnt/c/Users/Wells/Projects/Kubernates-Lessons/week1/task5/terraform
export TF_VAR_linode_token="YOUR_LINODE_TOKEN"
terraform destroy
```

## 可提交的內容

本題可提交以下內容：

1. Terraform 設定檔：`week1/task5/terraform`
2. Kubernetes manifests：`week1/task5/k8s`
3. 工作負載 apply / cleanup 腳本
4. 本 README 中的建立步驟、驗證結果與 cleanup 流程

## 參考文件

- [Deploy a Linode Kubernetes Engine Cluster Using Terraform](https://www.linode.com/docs/guides/deploy-lke-cluster-using-terraform/)
- [Using Terraform to Provision Linode Environments](https://www.linode.com/docs/guides/how-to-build-your-infrastructure-using-terraform-and-linode/)
- [LKE version updates v1.33 / v1.34](https://techdocs.akamai.com/cloud-computing/changelog/lke-v133-v134)
- [Linode API: List LKE Versions](https://techdocs.akamai.com/linode-api/reference/get-lke-versions)
- [Kubernetes Service type LoadBalancer](https://kubernetes.io/docs/concepts/services-networking/service/)
