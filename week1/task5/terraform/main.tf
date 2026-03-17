provider "linode" {
  token = var.linode_token
}

resource "linode_lke_cluster" "task5" {
  label       = var.cluster_label
  region      = var.region
  k8s_version = var.k8s_version
  tags        = ["week1", "task5"]

  pool {
    type  = var.node_pool_type
    count = var.node_count
  }
}
