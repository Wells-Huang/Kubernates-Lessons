## 實作題
1. 撰寫一個名為 deployment.yaml 的檔案，並用 kubectl 在本地 cluster 創建以下服務。
```
類型： Deployment
名稱： web-server
副本數 (Replicas)： 3
標籤 (Labels)： app: nginx
映像檔： nginx:1.14.2
容器埠號： 80
```
ANS: 
見 /week1/task1/deployment.yaml 檔案
執行 kubectl apply -f deployment.yaml 後，會建立一個名為 web-server 的 deployment，其中包含 3 個 replicas 的 nginx pod。

2. 使用 `kubectl get pods -o wide` 獲得這 3 個 Pod 的 IP 地址。

ANS: 
執行 kubectl get pods -o wide 後，會獲得以下結果：
```
NAME                          READY   STATUS    RESTARTS   AGE   IP           NODE    NOMINATED NODE   READINESS GATES
web-server-77bc6bd484-5k4wt   1/1     Running   0          18m   10.244.0.8   task1   <none>           <none>
web-server-77bc6bd484-f9x5s   1/1     Running   0          18m   10.244.0.7   task1   <none>           <none>
web-server-77bc6bd484-scn4r   1/1     Running   0          18m   10.244.0.9   task1   <none>           <none>
```

3. 嘗試用 jsonpath 抓出所有 Label 為 app: nginx 的 pod name，並用逗點分隔。 

ANS: 
執行 kubectl get pods -l app=nginx -o jsonpath="{range .items[*]}{.metadata.name}{','}{end}" 後，會獲得以下結果：
```
web-server-77bc6bd484-5k4wt,web-server-77bc6bd484-f9x5s,web-server-77bc6bd484-scn4r,
```

4. 使用 kubectl exec 進入其中一個 Pod，使用指令驗證網路互通。

ANS:
先執行 kubectl exec -it web-server-77bc6bd484-5k4wt -- bash 進入web-server-77bc6bd484-5k4wt 這個 pod。
接著用bash測試TCP是否可以連到另一個Pod的80 port。
echo > /dev/tcp/10.244.0.7/80 && echo TCP_CONNECT_OK
顯示為 TCP_CONNECT_OK，代表網路互通。

5. 手動刪除其中一個 Pod (kubectl delete pod <pod-name>)，觀察 Deployment 如何自動建立新 Pod。

ANS:
先執行 kubectl delete pod web-server-77bc6bd484-5k4wt 刪除一個Pod, 接著跑kubectl get pods -o wide
觀察 Deployment補上新的Pod

```
NAME                          READY   STATUS    RESTARTS   AGE   IP            NODE    NOMINATED NODE   READINESS GATES
web-server-77bc6bd484-6vp69   1/1     Running   0          13s   10.244.0.10   task1   <none>           <none>
web-server-77bc6bd484-f9x5s   1/1     Running   0          28m   10.244.0.7    task1   <none>           <none>
web-server-77bc6bd484-scn4r   1/1     Running   0          28m   10.244.0.9    task1   <none>           <none>
```

6. 嘗試創建 service.yaml，套用並建立 service 負責該 pods 的服務轉發，使用 NodePort type 的 Service，創建完成後，嘗試另外創建 pod 去 curl ClusterIp 來驗證該 Service 有正確轉發流量以及觀察 Nginx Pods 上的 logs。

ANS:
建立 service.yaml 檔案
接著執行 kubectl apply -f service.yaml，建立service/web-server-service
接著執行 kubectl get svc web-server-service -o wide，得到Cluster IP

NAME                 TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE   SELECTOR
web-server-service   NodePort   10.108.91.255   <none>        80:30080/TCP   42s   app=nginx

接著建立臨時Pod去curl Cluster IP

```
kubectl run curl-client --image=curlimages/curl:8.12.1 --restart=Never --command -- sleep 3600
kubectl wait --for=condition=Ready pod/curl-client --timeout=180s
kubectl exec curl-client -- curl -I http://web-server-service
```

回傳

```
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0HTTP/1.1 200 OK
Server: nginx/1.14.2
Date: Wed, 11 Mar 2026 14:22:25 GMT
Content-Type: text/html
Content-Length: 612
Last-Modified: Tue, 04 Dec 2018 14:44:49 GMT
Connection: keep-alive
ETag: "5c0692e1-264"
Accept-Ranges: bytes

  0   612    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0
```
看nginx logs

```
kubectl logs -l app=nginx --tail=20 --prefix=true
[pod/web-server-77bc6bd484-6vp69/nginx] 10.244.0.11 - - [11/Mar/2026:14:22:25 +0000] "HEAD / HTTP/1.1" 200 0 "-" "curl/8.12.1" "-"
[pod/web-server-77bc6bd484-f9x5s/nginx] 10.244.0.8 - - [11/Mar/2026:14:09:43 +0000] "" 400 0 "-" "-" "-"
```

7. 嘗試分別使用 NodePort 及 port forward 的方式，嘗試在本機網路去 curl 該 Service，並且說明兩者的差異以及如果我們希望做到 Service 分流的效果，我們該用兩者之中哪個方法？

Ans:
NodePort:
先查本地由minikube建立出來的cluster ip, 接著透過 NodePort 方式從本機去 curl 該 Service

```
minikube ip
curl.exe -I http://<minikube-ip>:30080
```
會顯示 curl: (28) Failed to connect to 172.17.0.4 port 30080 after 21051 ms: Could not connect to server , 連不上
cluster 是用 minikube 的 docker driver 跑在 Docker network 裡，minikube-ip 是 minikube node 在容器網路內的 IP，Windows 主機不一定能直接打到它。需要執行 minikube service web-server-service -p task1 --url 把 NodePort 對外轉成主機可連的網址。
此時curl這個網址就會回傳200

```
HTTP/1.1 200 OK
Server: nginx/1.14.2
Date: Thu, 12 Mar 2026 09:14:32 GMT
Content-Type: text/html
Content-Length: 612
Last-Modified: Tue, 04 Dec 2018 14:44:49 GMT
Connection: keep-alive
ETag: "5c0692e1-264"
Accept-Ranges: bytes
```

接著是Port Forward:
先執行 kubectl port-forward service/web-server-service 8080:80，出現
```
Forwarding from 127.0.0.1:8080 -> 80
Forwarding from [::1]:8080 -> 80
```
接著curl http://localhost:8080，會回傳200


NodePort 是透過 Service 對外提供固定節點埠口，比較接近正式服務入口。
port-forward 是把你本機某個 port 暫時轉到 cluster 裡的 Service，主要用來開發或除錯。

要做 Service 分流，應該用 NodePort 背後這種 Service 機制，不會選 port-forward，因為 port-forward 只是本機臨時通道，不是正式流量入口。

8. 嘗試使用 kubectl edit 更新 deployment 後，觀察 pod 的變化，並嘗試使用 rollback 退版及查看版本變化。

Ans:
先確認目前deployment

```
PS C:\Kubernates-Lessons> kubectl get deployment web-server
NAME         READY   UP-TO-DATE   AVAILABLE   AGE
web-server   3/3     3            3           21h

PS C:\Kubernates-Lessons> kubectl get pods -o wide
NAME                          READY   STATUS      RESTARTS       AGE   IP            NODE    NOMINATED NODE   READINESS GATES
curl-client                   0/1     Completed   0              20h   <none>        task1   <none>           <none>
web-server-77bc6bd484-6vp69   1/1     Running     1 (127m ago)   21h   10.244.0.13   task1   <none>           <none>
web-server-77bc6bd484-f9x5s   1/1     Running     1 (127m ago)   21h   10.244.0.14   task1   <none>           <none>
web-server-77bc6bd484-scn4r   1/1     Running     1 (127m ago)   21h   10.244.0.15   task1   <none>           <none>

PS C:\Kubernates-Lessons> kubectl rollout history deployment/web-server
deployment.apps/web-server 
REVISION  CHANGE-CAUSE
1         <none>
```

接著修改deployment
kubectl edit deployment web-server
把 image: nginx:1.14.2 改為 image: nginx:1.24.0 後存檔離開

接著輸入kubectl get pods -w
舊 Pod 逐步 Terminating，新 Pod 被建立出來。看到 3 個新 Pod 都變成 Running。

```
PS C:\Users\Wells\Projects\Kubernates-Lessons> kubectl get pods -w
NAME                          READY   STATUS      RESTARTS        AGE
curl-client                   0/1     Completed   0               23h
web-server-77bc6bd484-6vp69   1/1     Running     1 (4h37m ago)   23h
web-server-77bc6bd484-f9x5s   1/1     Running     1 (4h37m ago)   24h
web-server-77bc6bd484-scn4r   1/1     Running     1 (4h37m ago)   24h
web-server-d78996df7-fd8nr    0/1     Pending     0               0s
web-server-d78996df7-fd8nr    0/1     Pending     0               0s
web-server-d78996df7-fd8nr    0/1     ContainerCreating   0               0s
```


輸入kubectl rollout history deployment/web-server
會看到歷史紀錄
```
deployment.apps/web-server 
REVISION  CHANGE-CAUSE
1         <none>
2         <none>
```

接著做rollback
kubectl rollout undo deployment/web-server
使用 kubectl get pods -w 觀察變化

```
PS C:\Users\Wells\Projects\Kubernates-Lessons> kubectl get pods -w
NAME                          READY   STATUS      RESTARTS   AGE
curl-client                   0/1     Completed   0          23h
web-server-77bc6bd484-gcbk6   1/1     Running     0          3s
web-server-77bc6bd484-h6xv4   1/1     Running     0          5s
web-server-77bc6bd484-lxmwl   1/1     Running     0          7s
web-server-d78996df7-fd8nr    0/1     Completed   0          25m
web-server-d78996df7-fd8nr    0/1     Completed   0          25m
web-server-d78996df7-fd8nr    0/1     Completed   0          25m
```
最後再確認 rollback 後的版本和 image：
kubectl rollout history deployment/web-server
kubectl describe deployment web-server

```
PS C:\Kubernates-Lessons> kubectl rollout history deployment/web-server
>>
deployment.apps/web-server 
REVISION  CHANGE-CAUSE
2         <none>
3         <none>

PS C:\Kubernates-Lessons> kubectl describe deployment web-server
Name:                   web-server
Namespace:              default
CreationTimestamp:      Wed, 11 Mar 2026 21:43:25 +0800
Labels:                 <none>
Annotations:            deployment.kubernetes.io/revision: 3
Selector:               app=nginx
Replicas:               3 desired | 3 updated | 3 total | 3 available | 0 unavailable
StrategyType:           RollingUpdate
MinReadySeconds:        0
RollingUpdateStrategy:  25% max unavailable, 25% max surge
Pod Template:
  Labels:  app=nginx
  Containers:
   nginx:
    Image:         nginx:1.14.2
    Port:          80/TCP
    Host Port:     0/TCP
    Environment:   <none>
    Mounts:        <none>
  Volumes:         <none>
  Node-Selectors:  <none>
  Tolerations:     <none>
Conditions:
  Type           Status  Reason
  ----           ------  ------
  Available      True    MinimumReplicasAvailable
  Progressing    True    NewReplicaSetAvailable
OldReplicaSets:  web-server-d78996df7 (0/0 replicas created)
NewReplicaSet:   web-server-77bc6bd484 (3/3 replicas created)
Events:
  Type    Reason             Age   From                   Message
  ----    ------             ----  ----                   -------
  Normal  ScalingReplicaSet  26m   deployment-controller  Scaled up replica set web-server-d78996df7 from 0 to 1
  Normal  ScalingReplicaSet  26m   deployment-controller  Scaled down replica set web-server-77bc6bd484 from 3 to 2
  Normal  ScalingReplicaSet  26m   deployment-controller  Scaled up replica set web-server-d78996df7 from 1 to 2
  Normal  ScalingReplicaSet  26m   deployment-controller  Scaled down replica set web-server-77bc6bd484 from 2 to 1
  Normal  ScalingReplicaSet  26m   deployment-controller  Scaled up replica set web-server-d78996df7 from 2 to 3
  Normal  ScalingReplicaSet  26m   deployment-controller  Scaled down replica set web-server-77bc6bd484 from 1 to 0
  Normal  ScalingReplicaSet  103s  deployment-controller  Scaled up replica set web-server-77bc6bd484 from 0 to 1
  Normal  ScalingReplicaSet  101s  deployment-controller  Scaled down replica set web-server-d78996df7 from 3 to 2
  Normal  ScalingReplicaSet  101s  deployment-controller  Scaled up replica set web-server-77bc6bd484 from 1 to 2
  Normal  ScalingReplicaSet  99s   deployment-controller  Scaled down replica set web-server-d78996df7 from 2 to 1
  Normal  ScalingReplicaSet  99s   deployment-controller  Scaled up replica set web-server-77bc6bd484 from 2 to 3
  Normal  ScalingReplicaSet  97s   deployment-controller  Scaled down replica set web-server-d78996df7 from 1 to 0

```
revision 2是edit後的新版本，之後做了rollback，所以變成revision 3，內容是 nginx:1.14.2


9. 嘗試自己 build 一個新的 nginx image，用它創建一個新的 deployment "web-server-new"，以及與之對應的 service，嘗試在 dockerfile 中，加入 nginx 設定檔的設定，讓其可以將流量轉發至 web-server。
並且提供您如何驗證是否有成功的做法。

第九題流量順序應如以下：
client -> web-server-service-new -> web-server-new -> web-server-service -> web-server

Ans:
準備好4個檔案 (Dockerfile, nginx-new.conf, web-server-new.yaml, web-server-service-new.yaml)
首先build image, 使用minikube來build

```
minikube image build -p task1 -t custom-nginx-proxy:1.0 .
```

接著建立 deployment 和 service

```
kubectl apply -f web-server-new.yaml
kubectl apply -f web-server-service-new.yaml
```
確認image是否build成功(前3個AGE 13m的是前一題的web-server，後兩個10s的是新build的nginx-proxy)，以及service是否建立成功

```
PS C:\Kubernates-Lessons\week1\task1> kubectl get pods -o wide
NAME                             READY   STATUS      RESTARTS   AGE   IP            NODE    NOMINATED NODE   READINESS GATES
curl-client                      0/1     Completed   0          24h   <none>        task1   <none>           <none>
web-server-77bc6bd484-gcbk6      1/1     Running     0          13m   10.244.0.21   task1   <none>           <none>
web-server-77bc6bd484-h6xv4      1/1     Running     0          13m   10.244.0.20   task1   <none>           <none>
web-server-77bc6bd484-lxmwl      1/1     Running     0          13m   10.244.0.19   task1   <none>           <none>
web-server-new-b4d9cfd4d-njh7c   1/1     Running     0          10s   10.244.0.23   task1   <none>           <none>
web-server-new-b4d9cfd4d-zxslc   1/1     Running     0          10s   10.244.0.22   task1   <none>           <none>

PS C:\Kubernates-Lessons\week1\task1> kubectl get svc web-server-service-new -o wide
NAME                     TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE   SELECTOR
web-server-service-new   NodePort   10.96.101.120   <none>        80:30081/TCP   44s   app=nginx-proxy
```

驗證:
1. 先從 cluster 內驗證代理鏈：

執行kubectl exec curl-client -- curl -i http://web-server-service-new

```
PS C:\Kubernates-Lessons\week1\task1> kubectl exec curl-client -- curl -i http://web-server-service-new
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   612  100   612    0     0  48979      0 --:--:-- --:--:-- --:--:-- 51000
HTTP/1.1 200 OK
Server: nginx/1.27.5
X-Proxy-Layer: web-server-new

```
接著確認proxy-pod的log
kubectl logs -l app=nginx-proxy --tail=20 --prefix=true
看到nginx-proxy的log，確認有新的request紀錄
```
[pod/web-server-new-b4d9cfd4d-zxslc/nginx-proxy] 10.244.0.24 - - [12/Mar/2026:14:58:39 +0000] "GET / HTTP/1.1" 200 612 "-" "curl/8.12.1" "-"
```

接著確認web-server-new-pod的log
kubectl logs -l app=nginx --tail=20 --prefix=true，看到web-server-new-pod的log，確認有新的request紀錄
```
[pod/web-server-77bc6bd484-gcbk6/nginx] 10.244.0.22 - - [12/Mar/2026:14:58:39 +0000] "GET / HTTP/1.0" 200 612 "-" "curl/8.12.1" "10.244.0.24"
```
再對外測試，跑 minikube service web-server-service-new -p task1 --url
http://127.0.0.1:63754
接著執行curl，確認本機對外存取也成功。

```
PS C:\Kubernates-Lessons\week1\task1> curl.exe -i http://127.0.0.1:63754
HTTP/1.1 200 OK
Server: nginx/1.27.5
Date: Thu, 12 Mar 2026 15:18:50 GMT
Content-Type: text/html
Content-Length: 612
Connection: keep-alive
Last-Modified: Tue, 04 Dec 2018 14:44:49 GMT
ETag: "5c0692e1-264"
Accept-Ranges: bytes
X-Proxy-Layer: web-server-new
```
