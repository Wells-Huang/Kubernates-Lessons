# Week1 Task4

本題示範如何讓 Pod 透過 `ServiceAccount` 搭配 `RBAC` 權限，安全地呼叫 Kubernetes API，讀取指定 namespace 的 Pod 清單，並把結果輸出到 Pod logs。

這份 `README.md` 使用 UTF-8 編碼。

## 需求拆解

1. 建立可呼叫 Kubernetes API 的程式
2. 把程式打包成 Image
3. 建立 `ServiceAccount`、`Role`、`RoleBinding`
4. 用 Projected Volume 掛載 SA token，讓 Pod 在執行時呼叫 API，並把結果印到 logs

## 參考文件

- [Configure Service Accounts for Pods](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/)
- [Service Accounts](https://kubernetes.io/docs/concepts/security/service-accounts/)

## 本實作重點

- Pod 使用 `serviceAccountName` 指定身份
- Pod 設定 `automountServiceAccountToken: false`，避免使用預設自動掛載
- 改用 `projected` volume 明確掛載 token、CA 憑證與 namespace 資訊
- 透過 `Role` + `RoleBinding` 只授權讀取 `probe-lab` namespace 內的 Pods

## 架構說明

這次的權限設計如下：

- Pod 執行在 `sa-lab`
- `ServiceAccount` 也建立在 `sa-lab`
- `Role` 與 `RoleBinding` 建立在 `probe-lab`
- `RoleBinding` 綁定來自 `sa-lab` 的 `pod-reader-sa`

這個設計可以展示：Pod 雖然在 `sa-lab` 執行，但仍可透過 RBAC 被授權去讀取 `probe-lab` 裡的 Pods。

可以把 namespace 想成邏輯邊界，但不要把它完全等同成資料夾。真正負責授權的是 `Role` 與 `RoleBinding`；namespace 主要提供資源隔離與歸屬範圍。

在真實環境中，這很像監控系統放在自己的 namespace，例如 Prometheus 位於 `monitoring`，但被授權去讀取其他 namespace 的工作負載資訊。

## 運作流程

### 第一步：身份與權限的建立 (`rbac.yaml`)

Pod 要能呼叫 Kubernetes API，首先要有合適的身份與權限。

1. `ServiceAccount`：建立 `pod-reader-sa`，它是 Pod 對 API Server 表明身份時使用的憑證來源。
2. `Role`：在 `probe-lab` namespace 中建立 `pod-reader-role`，授予 `pods` 資源的 `get` 與 `list` 權限。
3. `RoleBinding`：把來自 `sa-lab` 的 `pod-reader-sa` 綁定到 `probe-lab` 的 `pod-reader-role`，讓這個身份可以讀取 `probe-lab` 內的 Pods。

### 第二步：掛載 Token 與憑證 (`pod.yaml`)

為了讓 Python 程式能安全呼叫 API Server，Pod 需要取得 token 與 CA 憑證。

1. `spec.serviceAccountName: pod-reader-sa`：指定這個 Pod 要使用哪個 ServiceAccount。
2. `automountServiceAccountToken: false`：關閉預設自動掛載，改用我們自己定義的 projected volume。
3. `projected` volume：把多個來源的資訊掛到同一個目錄下。

在這份設定裡，projected volume 來源有三個：
- `serviceAccountToken`：產生短效 token，寫入 `token` 檔案
- `configMap`：從 `kube-root-ca.crt` 取出 `ca.crt`
- `downwardAPI`：把 Pod 自己的 namespace 資訊寫入檔案

最後這個 volume 會掛到容器內的 `/var/run/secrets/pod-reader`。

### 第三步：準備 API 呼叫參數 (`app.py`)

程式執行時，需要知道 API Server 在哪裡，以及 token 和 CA 憑證檔案放在哪裡。

1. `build_api_url()` 會讀取 `KUBERNETES_SERVICE_HOST` 與 `KUBERNETES_SERVICE_PORT_HTTPS`。
2. 這兩個環境變數通常會由 Kubernetes 自動提供給 Pod，讓 Pod 知道 API Server 的內部位址。
3. 程式會從 `/var/run/secrets/pod-reader/token` 讀 token。
4. 程式會從 `/var/run/secrets/pod-reader/ca.crt` 讀 CA 憑證。

### 第四步：實際送出請求 (`fetch_pods()`)

1. 組合 API URL：`https://{host}:{port}/api/v1/namespaces/{TARGET_NAMESPACE}/pods`
2. 在 HTTP Header 中加入 `Authorization: Bearer {token}`
3. 用 `ssl.create_default_context(cafile=CA_FILE)` 驗證 API Server 憑證
4. 送出請求後解析 JSON，最後把 Pod 名稱印到 logs

## 操作步驟

### Step 1. 確認環境

```powershell
kubectl config current-context
minikube status -p task1
kubectl get nodes
kubectl get pods -n probe-lab
```

只要 `task1` 是 Running，且 `probe-lab` 裡面看得到 Pods，就可以往下做。

### Step 2. 用 Minikube 建立本機測試 image

```powershell
minikube image build -p task1 -t task4-pod-reader:local .\week1\task4
minikube image ls -p task1 | Select-String "task4-pod-reader"
```

### Step 3. 建立 namespace 與 RBAC

```powershell
kubectl apply -f .\week1\task4\namespace.yaml
kubectl apply -f .\week1\task4\rbac.yaml
kubectl get sa -n sa-lab
kubectl get rolebinding -n probe-lab
```
### Step 4. 建立使用 projected token 的 Pod
```powershell
kubectl apply -f .\week1\task4\pod-local.yaml
kubectl logs pod-reader -n sa-lab
```

預期 logs 會列出 `probe-lab` 內目前的 Pod 名稱。
建議先用 `kubectl get pod pod-reader -n sa-lab --watch` 觀察 Pod 進入 `Completed`，再查看 logs。

### Step 5. 推送到 Docker Hub 並使用公開 image 驗證

```powershell
docker build -t wellshuang814/k8s-pod-reader:week1-task4 .\week1\task4
docker push wellshuang814/k8s-pod-reader:week1-task4
kubectl delete pod pod-reader -n sa-lab --ignore-not-found=true
kubectl apply -f .\week1\task4\pod.yaml
kubectl wait --for=jsonpath='{.status.phase}'=Succeeded pod/pod-reader -n sa-lab --timeout=180s
kubectl logs pod-reader -n sa-lab
```

公開 image：

`wellshuang814/k8s-pod-reader:week1-task4`
