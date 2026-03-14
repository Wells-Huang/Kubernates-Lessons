# Week1 Task3

本題使用 readinessProbe 讓指定 Pod 停止接收 Service 流量，但 Pod 仍維持 Running，Nginx 也不會停止。
做法是讓 Pod 內部的檔案 /tmp/ready 消失，讓 readinessProbe 回傳失敗。

因為 readinessProbe 失敗，所以 Service 不會將該 Pod 加入 Endpoints，因此 Service 就無法將流量導向該 Pod。
這樣不需要刪除該Pod，也不需要關閉Nginx。
使用 readinessProbe 是因為失敗不會重啟容器，只會讓 Pod 變成 NotReady，並從 Service Endpoints 中移除。若改用 livenessProbe，失敗時會導致容器被 Kubernetes 重啟，這不符合本題「Pod 與 Nginx 都繼續存活，只停止接收流量」的需求。

建立資源：
kubectl apply -f week1/task3/namespace.yaml
kubectl apply -f week1/task3/deployment.yaml
kubectl apply -f week1/task3/service.yaml
kubectl apply -f week1/task3/curl-client.yaml
kubectl wait --for=condition=Available deployment/nginx-probe-demo -n probe-lab --timeout=180s
kubectl wait --for=condition=Ready pod/curl-client -n probe-lab --timeout=180s

初始檢查：
kubectl get pods -n probe-lab -o wide
kubectl get endpoints nginx-probe-service -n probe-lab -o wide
kubectl exec -n probe-lab curl-client -- sh -c "for i in 1 2 3 4 5 6; do wget -qO- http://nginx-probe-service | grep -o 'nginx-probe-demo[^<]*'; done"
預期會看到 3 個 Ready Pod，且請求會輪流落到不同 Pod。

讓單一 Pod 停止接流量：
kubectl get pods -n probe-lab
kubectl exec -n probe-lab pod-name -- rm /tmp/ready
kubectl get pods -n probe-lab -w
kubectl get endpoints nginx-probe-service -n probe-lab -o wide
預期被選中的 Pod 會從 1/1 變成 0/1，但狀態仍是 Running，Service endpoints 會從 3 個變成 2 個。

驗證 Nginx 仍活著：
kubectl get pod pod-name -n probe-lab -o wide
kubectl exec -n probe-lab curl-client -- curl -s http://pod-ip
如果仍能回到 HTML，表示 Nginx 沒停，只是被 readinessProbe 從 Service 分流名單中移除。

恢復流量：
kubectl exec -n probe-lab pod-name -- touch /tmp/ready
kubectl get endpoints nginx-probe-service -n probe-lab -o wide
