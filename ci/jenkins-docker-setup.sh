#!/bin/bash

# Jenkins Docker uad8cud55c uc124uc815 uc2a4ud06cub9bdud2b8

# Jenkins uc0acuc6a9uc790ub97c docker uadf8ub8f9uc5d0 ucd94uac00
sudo usermod -aG docker jenkins

# Docker uc18cucf13 uad8cud55c ubcc0uacbd
sudo chmod 666 /var/run/docker.sock

# Docker uc18cucf13 uc18cuc720uc790 ubcc0uacbd
sudo chown root:docker /var/run/docker.sock

# Jenkins uc11cube44uc2a4 uc7acuc2dcuc791
sudo systemctl restart jenkins

echo "Jenkins Docker uad8cud55c uc124uc815uc774 uc644ub8ccub418uc5c8uc2b5ub2c8ub2e4."
echo "Jenkins uc11cubc84uc5d0uc11c uc774 uc2a4ud06cub9bdud2b8ub97c uc2e4ud589ud574uc8fcuc138uc694."
