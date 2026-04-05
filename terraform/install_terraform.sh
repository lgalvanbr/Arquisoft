#!/bin/bash

# Script de instalación de Terraform usando tfenv.
# Este script es útil para los laboratorios 7, 8, 9 y 10 del curso ISIS2503 - Arquitectura de Software.

# Verifica si Terraform ya está instalado
if command -v terraform >/dev/null 2>&1; then
    echo "Terraform ya está instalado:"
    terraform --version
    exit 0
fi

# Clona el repositorio tfenv en el directorio ~/.tfenv para gestionar versiones de Terraform.
git clone https://github.com/tfutils/tfenv.git ~/.tfenv

# Crea el directorio ~/bin si no existe y crea enlaces simbólicos de los ejecutables de tfenv en ~/bin.
mkdir -p ~/bin
ln -s ~/.tfenv/bin/* ~/bin/

# Instala y usa la última versión disponible de Terraform usando tfenv.
tfenv install
tfenv use latest

# Configura el directorio de caché para Terraform.
mkdir -p ~/.terraform.d/plugin-cache
echo 'plugin_cache_dir = "C:\Users\ariad/.terraform.d/plugin-cache"' >> ~/.terraformrc

# Muestra la versión actual de Terraform instalada para verificar la instalación.
terraform --version
