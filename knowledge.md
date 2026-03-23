# Kubernetes Learning Notes

## Finalizer

`finalizer` 可以把它想成 Kubernetes 資源刪除前的清場註記。

當你執行 `kubectl delete` 時，Kubernetes 不一定會立刻把物件刪掉。若資源的 `metadata.finalizers` 有值，API Server 會先把資源標記為「正在刪除」：

- 寫入 `deletionTimestamp`
- 保留資源本體
- 等待對應 controller 完成善後

只有當 finalizer 被移除後，Kubernetes 才會真正刪掉該資源。

### 為什麼會卡在 Terminating

如果資源上有 finalizer，但負責收尾的 controller 已經不存在，資源就可能永遠卡在 `Terminating`。

典型現象：

- `kubectl get ... -o yaml` 看得到 `deletionTimestamp`
- `finalizers` 仍然存在
- 相關相依物件其實已經不在了
- 但資源就是不會消失

這不是 API Server 壞掉，而是：

- API Server 只負責記錄「要刪」
- 真正的清場邏輯要由 controller 執行
- controller 不在時，沒有人會移除 finalizer

### 什麼時候可以手動移除 finalizer

當你已經確認：

- 相依資源都刪掉了
- 對應 controller 已不在，無法自動收尾
- 留著只會一直卡住

這時可以手動 patch finalizer：

```powershell
kubectl patch <resource> <name> --type=merge -p '{\"metadata\":{\"finalizers\":[]}}'
```

這是在告訴 Kubernetes：

- 不再等待外部 controller 收尾
- 直接完成刪除流程

## Controller

Kubernetes 不是一個單一中央大腦，而是：

- API Server：接收與提供資源資料
- etcd：儲存資源狀態
- controllers：持續觀察資源，讓現實狀態靠近你宣告的理想狀態

可以把 controller 想成：

- 持續巡邏的自動管理員
- 負責某一類資源
- 發現實際狀態不符合宣告時，就自動修正

### 為什麼 Kubernetes 不自己清 finalizer

因為 API Server 並不知道外部善後邏輯。

例如：

- 某個 `Service type=LoadBalancer` 背後可能有外部雲端 Load Balancer
- 某個 `Gateway` 背後可能有 Envoy Deployment、Service 與動態設定
- 某個自訂 CRD 可能代表外部資料庫、DNS 或憑證

這些善後步驟只有對應 controller 才知道怎麼做，所以 finalizer 必須等 controller 來移除。

## 常見 Controllers

### Deployment controller

負責維持 Deployment 想要的 Pod 數量與版本。

例如你宣告：

```yaml
replicas: 3
```

如果實際只有 2 個 Pod，Deployment controller 會補 1 個。  
如果 rollout 更新 image，它也會按照策略建立新 ReplicaSet、逐步替換舊 Pod。

### StatefulSet controller

負責管理有身份與順序性的 Pod。

特色：

- Pod 名稱固定，例如 `mysql-0`、`mysql-1`
- 建立與刪除通常有順序
- 常搭配 PVC 使用

這也是為什麼 StatefulSet 的資料卷不一定會隨著 Pod 一起被刪除，因為它通常被視為需要保留的狀態資料。

### ingress-nginx controller

這是 Ingress 的實作者之一。

它負責：

- 監看 `Ingress`
- 讀取 `IngressClass`
- 產生與更新 NGINX 設定
- 把流量依照 host/path 規則轉送到正確的 Service

在 task8 裡它扮演的是：

- 入口流量控制器
- 依照 `Host: grafana.task8.local` 把請求轉到 Grafana Service

## Ingress / IngressClass / ingress-nginx controller 對照

### Ingress 是什麼

`Ingress` 是流量規則本身。

它描述：

- 哪個 hostname
- 哪個 path
- 要轉到哪個 Service

但它自己不會真的處理流量，它只是宣告規則。

例如：

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
spec:
  ingressClassName: nginx
  rules:
    - host: grafana.task8.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: grafana
                port:
                  number: 80
```

這代表：

- 當請求 host 是 `grafana.task8.local`
- 就轉送到 `service/grafana:80`

### IngressClass 是什麼

`IngressClass` 是派工資訊。

它描述：

- 這一類 Ingress 應該由哪個 Ingress Controller 處理

例如：

```yaml
apiVersion: networking.k8s.io/v1
kind: IngressClass
metadata:
  name: nginx
spec:
  controller: k8s.io/ingress-nginx
```

這代表：

- 名叫 `nginx` 的 class
- 對應 `ingress-nginx` controller

所以當某個 Ingress 寫：

```yaml
spec:
  ingressClassName: nginx
```

它就是在說：

- 這份流量規則要交給 `nginx` 這個 class 對應的 controller 處理

### ingress-nginx controller 是什麼

`ingress-nginx controller` 才是真正執行流量轉送的人。

它會監看：

- `Ingress`
- `IngressClass`
- `Service`
- `EndpointSlice`
- `Secret`

然後把規則翻譯成 NGINX 設定，讓 NGINX 真的幫你轉發流量。

### 三者關係

可以用一句話記：

- `Ingress` 決定「怎麼轉」
- `IngressClass` 決定「誰來做」
- `controller` 負責「真的去做」

### ingress-nginx chart 裡兩個容易混淆的設定

#### `controller.ingressClassResource.name`

這是在說：

- Helm 安裝時，要建立的 `IngressClass` 物件名稱是什麼

例如：

```yaml
controller:
  ingressClassResource:
    name: nginx
```

通常會建立出：

- `IngressClass/nginx`

所以它比較偏向「建立哪個 class 資源」。

#### `controller.ingressClass`

這是在說：

- 這個 `ingress-nginx controller` 自己要接手哪個 class 名稱

例如：

```yaml
controller:
  ingressClass: nginx
```

意思是：

- controller 看到 `ingressClassName: nginx` 的 Ingress，就會接手處理

所以它比較偏向「controller 自己認得哪個 class」。

### 為什麼兩者通常設成一樣

最常見做法是：

```yaml
controller:
  ingressClassResource:
    name: nginx
  ingressClass: nginx
```

這樣整條鏈會對得很直觀：

- 叢集裡建立 `IngressClass/nginx`
- controller 也宣告自己處理 `nginx`
- 你的 Ingress 再寫 `ingressClassName: nginx`

三者自然就接起來了。

### `watchIngressWithoutClass: false` 的意思

這代表：

- controller 不會接手那些沒有指定 `ingressClassName` 的 Ingress

好處是：

- 規則更明確
- 不容易誤接到別的 Ingress
- 在學習時比較容易理解資源是怎麼對上的

### Envoy Gateway controller

這是 Gateway API 的實作者之一。

它負責：

- 監看 `GatewayClass`、`Gateway`、`HTTPRoute`
- 驗證哪些 Gateway 應該由它管理
- 建立對應的 Envoy data plane Deployment / Service
- 把 Gateway API 規則翻譯成 Envoy 可執行的流量設定

在 task8 裡它扮演的是：

- Gateway API 的控制器
- 接手 `GatewayClass eg`
- 根據 `Gateway` / `HTTPRoute` 建出對外服務與路由規則

## Gateway API 與 Ingress 的對照

在這次 task8 裡，可以先用這個方式理解：

- `Ingress`
  - 較早期、較精簡的 HTTP/HTTPS 入口規則 API
- `Gateway API`
  - 較新、分工更清楚、可擴充性更高的入口 API

學習上可以先做這個粗略對照：

- `IngressClass`
  - 類似 Gateway API 裡的 `GatewayClass`
- `Ingress`
  - 概念上可拆成 `Gateway` + `HTTPRoute`
- `ingress-nginx controller`
  - 類似 Envoy Gateway controller

### 三個核心物件

#### `GatewayClass`

定義：

- 哪一種 Gateway controller 會接手這類 Gateway

它很像在說：

- 這個入口類型由誰來實作

#### `Gateway`

定義：

- 入口本身長什麼樣

例如：

- 開哪些 listener
- 用哪個 port
- 接哪些 hostname

可以把它想成：

- 入口設備或入口站點本身

#### `HTTPRoute`

定義：

- HTTP 流量怎麼轉送

例如：

- 某個 hostname
- 某個 path
- 要送到哪個 Service

可以把它想成：

- 真正的 HTTP 路由規則

### 這次 task8 的對應方式

Ingress 版本：

- `IngressClass/nginx`
- `Ingress`
- `ingress-nginx controller`

Gateway API 版本：

- `GatewayClass/eg`
- `Gateway`
- `HTTPRoute`
- `Envoy Gateway controller`

### 一句話記法

- `Ingress` 比較像把入口與路由規則放在同一個物件裡
- `Gateway API` 則把入口能力與路由規則拆開
- 所以 Gateway API 在中大型場景通常更清楚、更好擴充

## Task8 Cleanup 順序學到的事

若要避免卡 finalizer，理想順序通常是：

1. 刪除高階路由資源，例如 `HTTPRoute`
2. 刪除 `Gateway`
3. 刪除 `GatewayClass`
4. 確認不再有相依資源
5. 最後才卸載 controller

如果先把 controller 卸載掉，再刪還帶 finalizer 的資源，就可能需要手動 patch 才能解卡。
