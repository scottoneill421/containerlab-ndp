packer {
  required_plugins {
    qemu = { version = "~> 1.1", source = "github.com/hashicorp/qemu" }
  }
}

source "qemu" "ubuntu" {
  iso_url               = "https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img"
  iso_checksum          = "file:https://cloud-images.ubuntu.com/jammy/current/SHA256SUMS"
  disk_image            = true
  disk_size             = "20G"
  format                = "qcow2"
  accelerator           = "kvm"
  memory                = 2048
  cpus                  = 4
  ssh_username          = "ubuntu"
  ssh_private_key_file  = pathexpand("~/.ssh/id_ed25519")
  ssh_timeout           = "20m"
  vm_name               = "golden-containerlab-base.qcow2"
  output_directory      = "output-images"

  boot_command = [
    "<enter><wait5>",
    "<enter>"
  ]

  cd_label = "cidata"

  cd_content = {
    "meta-data" = "instance: packer-ubuntu\nlocal-hostname: ubuntu-base\n"
    "user-data" = <<-EOT
      #cloud-config
      users:
        - name: ubuntu
          sudo: ['ALL=(ALL) NOPASSWD:ALL']
          shell: /bin/bash
          ssh_authorized_keys:
            - ${file(pathexpand("~/.ssh/id_ed25519.pub"))}
    EOT
  }
}

build {
  sources = ["source.qemu.ubuntu"]

  provisioner "shell" {
    inline = [
      "sudo apt-get update && sudo apt-get install -y docker.io curl bridge-utils",
      "sudo systemctl enable --now docker",
      "curl -sL https://get.containerlab.dev | sudo bash"
    ]
  }
}
