terraform {
  required_version = ">= 1.4.0"

  required_providers {
    linode = {
      source  = "linode/linode"
      version = "~> 3.0"
    }
  }
}
