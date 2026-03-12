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

Port Forward:
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
9. 嘗試自己 build 一個新的 nginx image，用它創建一個新的 deployment "web-server-new"，以及與之對應的 service，嘗試在 dockerfile 中，加入 nginx 設定檔的設定，讓其可以將流量轉發至 web-server。
並且提供您如何驗證是否有成功的做法。

第九題流量順序應如以下：
client -> web-server-service-new -> web-server-new -> web-server-service -> web-server