# Week1 Task3

本題示範如何使用 `readinessProbe`，在不刪除 Pod、也不停止 Pod 內 Nginx 的前提下，讓指定 Pod 暫時停止接收 Service 流量。

這份 `README.md` 使用 UTF-8 編碼。

## 需求拆解

1. 建立一個有 3 個副本的 Nginx Deployment
2. 建立對應的 Service，讓流量能分流到多個 Pod
3. 透過 Probe 控制單一 Pod 是否可以接收流量
4. 驗證 Pod 雖然不再接流量，但仍然維持 Running，Nginx 也持續存活

## 參考文件

- [Liveness, Readiness, and Startup Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)

## 本實作重點

- 使用 `readinessProbe` 控制 Pod 是否加入 Service Endpoints
- 使用 `livenessProbe` 確認 Nginx 仍然存活
- 透過 `/tmp/ready` 作為手動切換 Ready / NotReady 的開關
- 使用 `curl-client` Pod 從 cluster 內部驗證 Service 分流結果

## 架構說明

這次的資源設計如下：

- namespace：`probe-lab`
- Deployment：`nginx-probe-demo`
- Service：`nginx-probe-service`
- 測試 Pod：`curl-client`

`nginx-probe-demo` 一共有 3 個 Pod，Service 會把流量分流到所有 Ready 的 Pod。

在這份實作裡，容器啟動時會先建立 `/tmp/ready`，因此一開始 3 個 Pod 都會通過 `readinessProbe`。如果手動刪除某個 Pod 裡的 `/tmp/ready`，該 Pod 的 `readinessProbe` 就會失敗，Kubernetes 會把它從 Service Endpoints 中移除。

這樣可以達成：

- Pod 仍然存在
- Pod 狀態仍是 `Running`
- Nginx 仍然存活
- Service 不再把流量導向該 Pod

這正是本題要求的效果。

## 運作流程

### 第一步：建立基本資源 (`namespace.yaml`、`deployment.yaml`、`service.yaml`)

1. `namespace.yaml` 建立 `probe-lab` namespace。
2. `deployment.yaml` 建立 `nginx-probe-demo` Deployment，副本數為 3。
3. `service.yaml` 建立 `nginx-probe-service`，把流量導向帶有 `app: nginx-probe-demo` 標籤的 Pod。

### 第二步：設定 Probe 行為 (`deployment.yaml`)

這份 Deployment 同時放入兩種 Probe：

1. `livenessProbe`
   - 使用 `httpGet` 檢查 `GET /`
   - 目的在於確認 Nginx 本身仍然活著
2. `readinessProbe`
   - 使用 `exec` 執行 `test -f /tmp/ready`
   - 目的在於確認這個 Pod 是否應該加入 Service 分流名單

這裡選擇 `readinessProbe` 作為解法，是因為它失敗時不會重啟容器，只會讓 Pod 變成 NotReady，並從 Service Endpoints 中移除。若改用 `livenessProbe`，失敗時會導致容器被 Kubernetes 重啟，不符合本題需求。

### 第三步：用檔案作為 Ready 開關

容器啟動時會執行以下動作：

1. 取得 Pod 自己的 hostname
2. 將 hostname 寫入 Nginx 首頁
3. 建立 `/tmp/ready`
4. 啟動 Nginx

因為首頁內容包含 Pod 名稱，所以後續可以透過 curl Service 回應，觀察流量目前落在哪一個 Pod。

### 第四步：讓單一 Pod 停止接流量

當我們對某一個 Pod 執行：

```powershell
kubectl exec -n probe-lab pod-name -- rm /tmp/ready
```

該 Pod 的 `readinessProbe` 會開始失敗。之後：

- `kubectl get pods` 會看到它從 `1/1` 變成 `0/1`
- Pod 狀態仍然是 `Running`
- Service Endpoints 會少掉這個 Pod 的 IP
- Service 流量不會再送到它

## 操作步驟

### Step 1. 確認環境

```powershell
kubectl config current-context
minikube status -p task1
kubectl get nodes
```

只要 `task1` 正常運作，且 `kubectl` 能連到 cluster，就可以往下做。

### Step 2. 建立 namespace、Deployment、Service 與測試 Pod

```powershell
kubectl apply -f .\week1\task3\namespace.yaml
kubectl apply -f .\week1\task3\deployment.yaml
kubectl apply -f .\week1\task3\service.yaml
kubectl apply -f .\week1\task3\curl-client.yaml
kubectl wait --for=condition=Available deployment/nginx-probe-demo -n probe-lab --timeout=180s
kubectl wait --for=condition=Ready pod/curl-client -n probe-lab --timeout=180s
```

### Step 3. 確認初始分流狀態

```powershell
kubectl get pods -n probe-lab -o wide
kubectl get endpoints nginx-probe-service -n probe-lab -o wide
kubectl exec -n probe-lab curl-client -- sh -c "for i in 1 2 3 4 5 6; do wget -qO- http://nginx-probe-service | grep -o 'nginx-probe-demo[^<]*'; done"
```

預期會看到：

- `nginx-probe-demo` 有 3 個 `1/1 Running` 的 Pod
- `nginx-probe-service` 有 3 個 endpoints
- curl 結果會輪流出現不同的 Pod 名稱

### Step 4. 讓單一 Pod 停止接流量

```powershell
kubectl get pods -n probe-lab
kubectl exec -n probe-lab pod-name -- rm /tmp/ready
kubectl get pods -n probe-lab -w
kubectl get endpoints nginx-probe-service -n probe-lab -o wide
```

預期會看到被選中的 Pod 從 `1/1` 變成 `0/1`，但狀態仍是 `Running`，而且 Service endpoints 會從 3 個變成 2 個。

### Step 5. 驗證 Nginx 仍然活著

```powershell
kubectl get pod pod-name -n probe-lab -o wide
kubectl exec -n probe-lab curl-client -- curl -s http://pod-ip
```

如果仍能回到 HTML，表示 Nginx 並沒有停止，只是這個 Pod 已經被從 Service 分流名單中移除。

### Step 6. 恢復流量

```powershell
kubectl exec -n probe-lab pod-name -- touch /tmp/ready
kubectl get endpoints nginx-probe-service -n probe-lab -o wide
```

恢復後，該 Pod 會重新回到 Service Endpoints，Service 也會再把流量分配給它。
