output "cluster_id" {
  value = linode_lke_cluster.task5.id
}

output "status" {
  value = linode_lke_cluster.task5.status
}

output "api_endpoints" {
  value = linode_lke_cluster.task5.api_endpoints
}

output "kubeconfig" {
  value     = linode_lke_cluster.task5.kubeconfig
  sensitive = true
}
