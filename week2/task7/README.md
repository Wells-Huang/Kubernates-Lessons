# Week2 Task7

本題目標是熟悉 Helm Chart 的基本開發流程，並將 chart 推送到 hosted Helm registry，再從 public OCI registry 安裝到本機 Kubernetes 環境。

## 需求整理

1. 閱讀 Helm 官方文件，理解 Helm Chart 的基本結構與模板語法。
2. 建立自己的 Helm Chart，至少包含 `templates/` 與 `values.yaml`。
3. 本次實作使用 nginx Deployment，並將 replicas 放在 `values.yaml` 中控制。
4. 選擇一個 hosted Helm registry，將 chart push 上去並設定為 public。
5. 在本機 Kubernetes 環境中，從該 public registry 安裝這個 chart。

## 本題選擇

- Helm registry：Docker Hub
- Kubernetes 環境：Minikube profile `task1`
- Chart 名稱：`task7-nginx`
- Docker Hub OCI 路徑：`oci://registry-1.docker.io/<dockerhub-username>/task7-nginx`

## 參考文件

- [Helm Chart Template Guide - Getting Started](https://helm.sh/docs/chart_template_guide/getting_started/)
- [Helm Registries](https://helm.sh/docs/topics/registries/)
- [Docker Hub - Helm charts as OCI artifacts](https://docs.docker.com/docker-hub/oci-artifacts/helm-charts/)

## 環境確認

2026-03-18 實際確認結果：

- `docker` 可用
- `kubectl` 可用
- Minikube profile `task1` 存在
- active kube context 為 `task1`
- node `task1` 狀態為 `Ready`
- Helm 已放在 repo 內：`C:\Users\Wells\Projects\Kubernates-Lessons\.tools\helm\helm.exe`

Helm 路徑設定：

```powershell
$helm = (Resolve-Path .\.tools\helm\helm.exe).Path
```

## Registry 路徑說明

本題使用 Docker Hub 的 OCI registry，因此 `helm push` 與 `helm install` 的路徑格式不同：

- `helm push` 目標：`oci://registry-1.docker.io/<dockerhub-username>`
- `helm install` 來源：`oci://registry-1.docker.io/<dockerhub-username>/task7-nginx`

注意：`helm push` 時不要手動再加一次 chart 名稱，Helm 會自動附加 chart basename。

## 檔案結構

```text
week2/task7/
├─ Chart.yaml
├─ values.yaml
├─ templates/
│  ├─ _helpers.tpl
│  ├─ deployment.yaml
│  └─ service.yaml
├─ dist/
│  └─ task7-nginx-0.1.0.tgz
└─ README.md
```

## Chart 說明

這個 Helm Chart 會建立：

- 一個 nginx `Deployment`
- 一個對應的 `ClusterIP Service`

其中 `values.yaml` 內容如下：

```yaml
replicaCount: 2

image:
  repository: nginx
  tag: "1.27.5-alpine"
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80

containerPort: 80
```

重點是 `replicaCount` 由 `values.yaml` 控制，因此符合題目要求。

## 實作步驟

### Step 1. 驗證 chart

```powershell
& $helm lint .\week2\task7
& $helm template task7-demo .\week2\task7
```

驗證重點：

- `lint` 成功
- `template` 產出的 Deployment 中，`spec.replicas` 為 `2`

若要覆寫 replicas：

```powershell
& $helm template task7-demo .\week2\task7 --set replicaCount=3
```

### Step 2. 先安裝本地 chart 到 Minikube

```powershell
kubectl create namespace week2-task7 --dry-run=client -o yaml | kubectl apply -f -
& $helm upgrade --install task7-demo .\week2\task7 -n week2-task7
kubectl wait --for=condition=available deployment/task7-demo-task7-nginx -n week2-task7 --timeout=180s
kubectl get all -n week2-task7
```

### Step 3. 打包 chart

```powershell
New-Item -ItemType Directory -Force -Path .\week2\task7\dist | Out-Null
& $helm package .\week2\task7 --destination .\week2\task7\dist
```

輸出檔案：

```text
week2\task7\dist\task7-nginx-0.1.0.tgz
```

### Step 4. 登入 Docker Hub

先在 Docker Hub 建立一個 public repository，例如：

```text
task7-nginx
```

若使用 GitHub 第三方登入 Docker Hub，CLI 建議直接使用：

```powershell
docker login
```

此流程會沿用 Docker Hub 的網頁登入機制，因此不需要輸入 GitHub 密碼。

### Step 5. Push chart 到 Docker Hub

正確指令：

```powershell
& $helm push .\week2\task7\dist\task7-nginx-0.1.0.tgz oci://registry-1.docker.io/<dockerhub-username>
```

實際成功結果：

```text
Pushed: registry-1.docker.io/<dockerhub-username>/task7-nginx:0.1.0
Digest: sha256:<chart-digest>
```

### Step 6. 從 public registry 安裝 chart

先移除本地測試 release：

```powershell
& $helm uninstall task7-demo -n week2-task7
```

再從 Docker Hub OCI registry 安裝：

```powershell
& $helm install task7-public oci://registry-1.docker.io/<dockerhub-username>/task7-nginx --version 0.1.0 -n week2-task7
kubectl wait --for=condition=available deployment/task7-public-task7-nginx -n week2-task7 --timeout=180s
kubectl get all -n week2-task7
```

### Step 7. 驗證 nginx 服務

執行 `port-forward` 後，該終端機會持續占用連線，因此建議另外開一個終端機執行 `curl`。

```powershell
kubectl port-forward -n week2-task7 service/task7-public-task7-nginx 8080:80
curl.exe -I http://127.0.0.1:8080
```

實際成功結果：

```http
HTTP/1.1 200 OK
Server: nginx/1.27.5
Date: Wed, 18 Mar 2026 14:24:50 GMT
Content-Type: text/html
Content-Length: 615
```

## 驗收結果

本題已完成以下項目：

1. 已閱讀 Helm 官方 getting started 與 registry 文件。
2. 已建立自己的 Helm Chart，包含 `templates/` 與 `values.yaml`。
3. 已使用 `values.yaml` 控制 nginx Deployment 的 replicas。
4. 已將 chart push 到 Docker Hub public OCI registry。
5. 已從 public registry 成功安裝到本機 Minikube 環境。
6. 已透過 `port-forward` 與 `curl` 驗證 nginx 回應 `200 OK`。

## 結論

本次實作完成了一個可用的 Helm Chart，並成功將其推送到 Docker Hub 的 public OCI registry。之後再從 registry 安裝到本機 Minikube 環境，最後以 HTTP 回應 `200 OK` 驗證服務可正常運作，符合題目要求。

## Cleanup

```powershell
& $helm uninstall task7-public -n week2-task7
kubectl delete namespace week2-task7
```

