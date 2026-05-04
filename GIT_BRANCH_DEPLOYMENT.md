# Git Branch Deployment - Guía Completa

## 📋 Descripción

Con los cambios en `deployment.tf`, ahora puedes desplegar **cualquier rama de Git** en AWS, no solo `main`.

Esto permite:
- ✅ Desplegar rama `auth` (cambios Auth0) sin afectar `main`
- ✅ Desplegar rama `feature-x` para testing
- ✅ Rollback a `main` en segundos si algo falla
- ✅ Garantizar estado limpio en cada deployment (determinístico)

---

## 🚀 Flujo de Despliegue por Rama

### Opción 1: Default (main)
```bash
cd terraform
terraform apply -auto-approve
```
**Resultado:** Despliega rama `main` (comportamiento anterior)

---

### Opción 2: Especificar rama diferente
```bash
cd terraform
terraform apply -auto-approve -var="git_branch=auth"
```
**Resultado:** Despliega rama `auth` en lugar de `main`

---

### Opción 3: Usar archivo terraform.tfvars
```bash
# 1. Copiar template
cp terraform.tfvars.example terraform.tfvars

# 2. Editar terraform.tfvars
# git_branch = "auth"

# 3. Aplicar
cd terraform
terraform apply -auto-approve
```

---

## 📝 Ejemplos Prácticos

### Escenario 1: Trabajas en rama `auth`, quieres desplegar cambios

```bash
# Estás en rama local:
$ git branch
  main
* auth
  feature-x

# Hiciste cambios en auth:
$ git status
On branch auth
Your branch is ahead of 'origin/auth' by 3 commits.

# Push a origin/auth
git push origin auth

# Deploy rama auth a AWS
cd terraform
terraform apply -auto-approve -var="git_branch=auth"

# ← Terraform:
#   ├─ Lee variable: git_branch = "auth"
#   ├─ En instancia EC2:
#   │  ├─ git clone --branch auth https://github.com/.../Arquisoft.git
#   │  ├─ git reset --hard origin/auth  ← Fuerza sync
#   │  └─ ✓ Código de rama auth en /apps/Arquisoft
#   ├─ Instala dependencies
#   ├─ Corre migraciones
#   └─ Arranca servidor
```

---

### Escenario 2: Deploy de auth falla, rollback a main

```bash
# Si algo salió mal con auth, volver a main es instantáneo:
terraform apply -auto-approve -var="git_branch=main"

# ← Terraform:
#   ├─ Destruye instances de auth
#   ├─ Crea nuevas instances
#   ├─ En instancia EC2:
#   │  └─ git clone --branch main https://github.com/.../Arquisoft.git
#   └─ ✓ Código de rama main en /apps/Arquisoft
```

---

### Escenario 3: Feature branch para testing

```bash
# En local: creas rama para feature
git checkout -b feature-security-enhancements
# ... haces cambios
git push origin feature-security-enhancements

# En AWS: desplegar feature para testing
terraform apply -auto-approve -var="git_branch=feature-security-enhancements"

# ← Terraform automáticamente:
#   ├─ Clona rama feature-security-enhancements
#   ├─ Instala todo
#   ├─ Arranca servidor
#   └─ Testing en AWS ✓

# Si tests pasan, merge a main:
git checkout main
git pull
git merge feature-security-enhancements
git push origin main

# Deploy final a producción:
terraform apply -auto-approve -var="git_branch=main"
```

---

## 🔧 Cómo Funciona Internamente

### Script en user_data (deployment.tf):

```bash
# Variables seteadas por Terraform:
BRANCH="${local.branch}"        # ← Viene de var.git_branch

# 1. Eliminar directorio anterior (estado limpio)
rm -rf "$APP_DIR"

# 2. Clonar rama específica
git clone --branch "$BRANCH" "$REPO" "$APP_DIR"

# 3. Si falla (rama no existe), fallback a main
# → git clone "$REPO" "$APP_DIR"
# → git checkout main

# 4. Sincronizar forzadamente
git fetch origin "$BRANCH"
git reset --hard origin/"$BRANCH"  ← Descarta cambios locales

# Resultado:
# ✓ Instancia siempre tiene código limpio de rama especificada
# ✓ Determinístico - no depende de estado previo
# ✓ Sincronizado con origin - no hay divergencias
```

---

## ✅ Checklist de Despliegue

### Antes de desplegar rama auth:

- [ ] Push a `origin/auth`: `git push origin auth`
- [ ] Verificar que rama existe remotamente: `git branch -r | grep auth`
- [ ] Revisar cambios en rama: `git log auth -5 --oneline`

### Desplegar:

- [ ] Ejecutar: `terraform apply -auto-approve -var="git_branch=auth"`
- [ ] Esperar 2-3 min a que instancias arranquen
- [ ] Revisar logs: SSH a instancia y `tail -f /var/log/cloudynet-setup.log`
- [ ] Verificar rama actual: `git branch` en `/apps/Arquisoft`

### Post-deployment:

- [ ] Acceder a http://<IP>:8080
- [ ] Probar funcionalidades
- [ ] Monitorear logs de Django
- [ ] Si hay error, rollback a main: `terraform apply -auto-approve -var="git_branch=main"`

---

## 🐛 Troubleshooting

### Problema: "fatal: Remote branch auth not found"

```bash
# Solución 1: La rama no está en origin
git push origin auth

# Solución 2: Rama local pero no en origin
git branch -r  # Ver ramas remotas
git push origin <rama>  # Push rama
```

### Problema: Terraform intenta clonar pero falla

```bash
# Ver logs en instancia:
ssh -i key.pem ec2-user@<IP>
tail -100 /var/log/cloudynet-setup.log | grep -i "clone\|branch\|error"

# El script tiene fallback a main, así que:
# - Si rama especificada no existe → usa main
# - Si main tampoco existe → error (repositorio corrupto)
```

### Problema: Cambios locales en instancia se pierden

**Esto es intencional** (por `git reset --hard`):
- El script siempre fuerza sincronización
- Cambios locales hechos en la instancia se descartan
- Esto garantiza reproducibilidad

**Solución:** Si necesitas persistencia, comitea cambios a rama en origen primero.

---

## 📊 Comparación: Antes vs Después

### Antes (INCORRECTO):
```
rama local: main
rama local: auth ← aquí estás
terraform apply
↓
Instancia descarga: main  ← ✗ Siempre main, no respeta tu rama
```

### Después (CORRECTO):
```
rama local: main
rama local: auth ← aquí estás
terraform apply -var="git_branch=auth"
↓
Instancia descarga: auth  ← ✓ Respeta tu rama actual
```

---

## 🎯 Casos de Uso Recomendados

### 1. Development (rama develop)
```bash
terraform apply -auto-approve -var="git_branch=develop"
```
- Cambios frecuentes
- Testing en AWS sin afectar staging/prod

### 2. Staging (rama staging)
```bash
terraform apply -auto-approve -var="git_branch=staging"
```
- QA testing
- Cambios estables pero no en producción

### 3. Production (rama main)
```bash
terraform apply -auto-approve -var="git_branch=main"
```
- Código testado y aprobado
- Último estado estable

### 4. Hotfixes (rama hotfix-xxx)
```bash
terraform apply -auto-approve -var="git_branch=hotfix-security-patch"
```
- Fix urgente en producción
- Después mergear a main

---

## 💡 Tips Profesionales

### Tip 1: Script de deployment automático

```bash
#!/bin/bash
# deploy.sh - Script que pregunta rama y despliega

echo "Ramas disponibles:"
git branch -r | grep -v HEAD

read -p "¿Qué rama desplegar? " BRANCH

cd terraform
terraform apply -auto-approve -var="git_branch=$BRANCH"
echo "Deployment de rama $BRANCH completado"
```

### Tip 2: Backup antes de desplegar rama experimental

```bash
# Si vas a desplegar rama experimental:
# 1. Apunta instancias actuales a un backup
terraform state pull > terraform.state.backup

# 2. Despliega rama experimental
terraform apply -auto-approve -var="git_branch=experimental"

# 3. Si falla, restaura:
terraform state push terraform.state.backup
```

### Tip 3: Monitoreo post-deployment

```bash
# En instancia, verificar que rama correcta está activa:
ssh -i key.pem ec2-user@<IP> \
  "cd /apps/Arquisoft && git status && git log -1 --oneline"

# Salida esperada:
# On branch auth
# Your branch is up to date with 'origin/auth'.
# 1a2b3c4 (HEAD -> auth) Fix Auth0 integration
```

---

## 📚 Referencias

- [Git Branching Workflows](https://www.atlassian.com/git/tutorials/comparing-workflows)
- [Terraform Variables](https://www.terraform.io/language/values/variables)
- [Git Reset --hard](https://git-scm.com/docs/git-reset)
