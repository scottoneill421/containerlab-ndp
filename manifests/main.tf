terraform {
  required_version = ">= 1.5.0"
  required_providers {
    libvirt = {
      source  = "dmacvicar/libvirt"
      version = "~> 0.8.0"
    }
  }
}

variable "lab_id" {
  type = string
}

variable "ssh_user" {
  type = string
}

variable "ssh_pubkey" {
  type = string
}

variable "base_image_path" {
  type    = string
  default = "/var/lib/libvirt/images/golden-containerlab-base.qcow2"
}

provider "libvirt" {
  uri = "qemu+ssh://${var.ssh_user}@172.16.32.2/system?no_verify=1&sshauth=privkey&keyfile=/home/${var.ssh_user}/.ssh/id_ed25519" 
}

resource "libvirt_pool" "pool" {
  name = "pool-${var.lab_id}"
  type = "dir"
  target { path = "/var/lib/libvirt/images/emulation-${var.lab_id}" }
}

resource "libvirt_volume" "base" {
  name   = "base-${var.lab_id}.qcow2"
  pool   = libvirt_pool.pool.name
  source = var.base_image_path # Packer image
  format = "qcow2"
}

resource "libvirt_cloudinit_disk" "init" {
  name      = "init-${var.lab_id}.iso"
  pool      = libvirt_pool.pool.name
  user_data = templatefile("${path.module}/cloud-init.yaml.tftpl", {
    ssh_pub_key = var.ssh_pub_key
  })
}

resource "libvirt_domain" "engine" {
  name      = "engine-${var.lab_id}"
  memory    = 16384
  vcpu      = 4
  arch      = "x86_64"
  machine   = "q35"
  cloudinit = libvirt_cloudinit_disk.init.id

  cpu { mode = "host-passthrough" }

  disk { volume_id = libvirt_volume.base.id }
  network_interface { 
    network_name = "default" 
  }
}

output "engine_ip" {
  value = libvirt_domain.engine.network_interface[0].addresses[0]
}
