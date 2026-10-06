#!/usr/bin/env bash
# check_prereqs.sh — detect missing kubectl + minikube prerequisites for the
# current OS/distro and print the exact install command for each gap.
#
# Usage:
#   check_prereqs.sh
#
# Output: Markdown to stdout.
# Exit code: 0 if nothing is missing, 1 if anything is missing.
#
# Full command reference: rules/minikube-setup.md

set -euo pipefail

missing=0
report=()

add_missing() {
  missing=1
  report+=("- **Missing:** $1")
  report+=("  **Install:** \`$2\`")
}

have() {
  command -v "$1" >/dev/null 2>&1
}

OS="$(uname -s)"
ARCH="$(uname -m)"

echo "## Kubernetes prerequisite check ($OS $ARCH)"
echo

# --- kubectl (all platforms) ---
if ! have kubectl; then
  case "$OS" in
  Darwin)
    add_missing "kubectl" "brew install kubectl"
    ;;
  Linux)
    add_missing "kubectl" "curl -LO \"https://dl.k8s.io/release/\$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl\" && sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl"
    ;;
  MINGW* | MSYS* | CYGWIN*)
    add_missing "kubectl" "winget install -e --id Kubernetes.kubectl"
    ;;
  *)
    add_missing "kubectl (unrecognized OS: $OS)" "see https://kubernetes.io/docs/tasks/tools/"
    ;;
  esac
else
  echo "- kubectl: $(kubectl version --client --output=json 2>/dev/null | grep gitVersion | head -1 | sed 's/[",]//g' | awk '{print $2}')"
fi

# --- minikube (all platforms) ---
if ! have minikube; then
  case "$OS" in
  Darwin)
    add_missing "minikube" "brew install minikube"
    ;;
  Linux)
    add_missing "minikube" "curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64 && sudo install minikube-linux-amd64 /usr/local/bin/minikube"
    ;;
  MINGW* | MSYS* | CYGWIN*)
    add_missing "minikube" "winget install -e --id Kubernetes.minikube"
    ;;
  *)
    add_missing "minikube (unrecognized OS: $OS)" "see https://minikube.sigs.k8s.io/docs/start/"
    ;;
  esac
else
  echo "- minikube: $(minikube version --short 2>/dev/null)"
fi

# --- Driver detection: at least one usable driver must be present ---
driver_found=""
if have docker && docker info >/dev/null 2>&1; then
  driver_found="docker"
  echo "- docker: present and running"
elif have docker; then
  echo "- docker: installed but daemon not running (start Docker Desktop or 'sudo systemctl start docker')"
fi

if [ -z "$driver_found" ]; then
  case "$OS" in
  Darwin)
    if [ "$ARCH" = "arm64" ]; then
      if have qemu-system-aarch64; then
        driver_found="qemu"
        echo "- qemu: present (Apple Silicon fallback)"
      else
        add_missing "A minikube driver (docker or qemu)" "brew install --cask docker   # OR for Apple Silicon without Docker Desktop: brew install qemu"
      fi
    else
      add_missing "A minikube driver (docker)" "brew install --cask docker"
    fi
    ;;
  Linux)
    # kvm2 needs BOTH the driver binary AND access to /dev/kvm — presence of either alone is a false positive.
    if have docker-machine-driver-kvm2 && [ -r /dev/kvm ]; then
      driver_found="kvm2"
      echo "- kvm2: driver binary + /dev/kvm present"
    else
      add_missing "A minikube driver (docker preferred)" "see https://docs.docker.com/engine/install/ and then: sudo usermod -aG docker \$USER && newgrp docker"
    fi
    ;;
  MINGW* | MSYS* | CYGWIN*)
    add_missing "A minikube driver (docker preferred)" "winget install -e --id Docker.DockerDesktop"
    ;;
  esac
fi

# --- Current cluster state (informational, not a gap) ---
if have minikube; then
  state="$(minikube status --format='{{.Host}}' 2>/dev/null || echo 'Unknown')"
  echo "- minikube status: $state"
fi

if have kubectl; then
  ctx="$(kubectl config current-context 2>/dev/null || echo 'none')"
  echo "- kubectl current-context: $ctx"
fi

echo
if [ "$missing" -eq 0 ]; then
  echo "**Result: all detected prerequisites present.**"
else
  echo "### Gaps found"
  echo
  printf '%s\n' "${report[@]}"
  echo
  echo "**Confirm with the user before running any \`sudo\`, \`brew install\`, or \`winget install\` command above — these modify system-wide state.**"
fi

exit "$missing"
