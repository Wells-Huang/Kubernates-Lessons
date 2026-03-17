variable "linode_token" {
  description = "Linode Personal Access Token with read/write access."
  type        = string
  sensitive   = true
}

variable "cluster_label" {
  description = "Cluster name shown in Linode Cloud Manager."
  type        = string
  default     = "week1-task5-lke"
}

variable "region" {
  description = "Linode region for the LKE cluster."
  type        = string
  default     = "us-central"
}

variable "k8s_version" {
  description = "LKE Kubernetes version."
  type        = string
  default     = "1.34"
}

variable "node_pool_type" {
  description = "Linode plan type for each worker node."
  type        = string
  default     = "g6-standard-2"
}

variable "node_count" {
  description = "Number of nodes in the default node pool."
  type        = number
  default     = 3

  validation {
    condition     = var.node_count >= 1
    error_message = "node_count must be at least 1."
  }
}
