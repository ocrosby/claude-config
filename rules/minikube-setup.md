---
name: minikube-setup
description: Local-learning Kubernetes environment setup — kubectl and minikube installation, driver choice, resource floors, essential addons, and the macOS-specific access-path quirks (LoadBalancer tunnel, image loading, NodePort). Single source of truth for prerequisite detection.
type: rule
---

# Minikube and kubectl Setup

Running Kubernetes locally fails for reasons that have nothing to do with Kubernetes — the wrong driver on the wrong CPU, 2 GiB of RAM starving the control plane, a NodePort that isn't reachable from the host, a `LoadBalancer` stuck in `<pending>` because the user never ran `tunnel`. Diagnosing that mid-tutorial is wasted time. This rule is the single source of truth for detecting and installing a working local K8s environment; `skills/kubernetes/SKILL.md` invokes it, it does not restate it.

Sources: https://kubernetes.io/docs/tasks/tools/ (kubectl install) and https://minikube.sigs.k8s.io/docs/start/ (minikube install). Verify against the live pages if a command below appears stale — package names and recommended drivers do change.

## Recognition Signals — what's missing and how to install it

| Signal (command exits non-zero or binary absent) | Platform | Install command |
|---|---|---|
| `kubectl version --client` fails | macOS | `brew install kubectl` |
| `kubectl version --client` fails | Linux (apt) | `curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl` |
| `kubectl version --client` fails | Windows | `winget install -e --id Kubernetes.kubectl` |
| `minikube version` fails | macOS | `brew install minikube` |
| `minikube version` fails | Linux (apt) | `curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64 && sudo install minikube-linux-amd64 /usr/local/bin/minikube` |
| `minikube version` fails | Windows | `winget install -e --id Kubernetes.minikube` |
| `docker info` fails on macOS | macOS | Install Docker Desktop (`brew install --cask docker`) — the Docker Desktop app must be running before `minikube start`. Alternative: `brew install podman && podman machine init && podman machine start` then `minikube start --driver=podman` |
| `docker info` fails on Linux | Linux | Install Docker Engine per https://docs.docker.com/engine/install/, then add user to `docker` group: `sudo usermod -aG docker $USER && newgrp docker` |
| Apple Silicon host, no Docker Desktop license, needs an alternative | macOS (M1/M2/M3) | `brew install qemu` then `minikube start --driver=qemu` — slower than Docker but license-free |
| `minikube status` reports `Stopped` or `Nonexistent` on first run | All | `minikube start` (see driver + resources below) |

## Mandatory Behaviors

**Always run the detection script before scaffolding a tutorial or starting a cluster.** Do not ask the user to eyeball their toolchain — run:

```bash
bash ~/.claude/skills/kubernetes/check_prereqs.sh
```

It prints exactly what's missing and the exact install command for the detected OS/distro, and exits `0` when nothing is missing, `1` otherwise. Never re-run a full install pass when the script reports everything present.

**Confirm before running any command that installs system-wide packages.** `brew install`, `winget install`, `apt install`, and anything with `sudo` modify shared machine state outside the project — state the exact command and get explicit confirmation before running it. Checking versions (`--version`, `--help`) does not require confirmation.

**Pick the driver by signal, not by habit.**

| Signal | Driver |
|---|---|
| macOS Intel or Apple Silicon with Docker Desktop installed and running | `docker` (default — easiest, best integration) |
| Apple Silicon without Docker Desktop (license concerns) | `qemu` (via `brew install qemu`) |
| Linux with Docker Engine installed | `docker` |
| Linux with `kvm2` available (`virt-host-validate` passes) | `kvm2` (lower overhead than Docker-in-VM) |
| Windows with WSL 2 + Docker Desktop | `docker` |
| Windows without Docker Desktop | `hyperv` (requires Hyper-V enabled, admin privileges) |
| Container runtime already present via Podman | `podman` (set `rootless: false` for first-time setups) |

Avoid `virtualbox` on Apple Silicon (broken) and `hyperkit` anywhere (deprecated as of minikube 1.31). If a user asks for one of those by name, name the deprecation and recommend the replacement.

**Set the resource floor before the first `start`, not after.** Default is 2 CPU / 2 GiB RAM — insufficient for `metrics-server`, `ingress`, and most tutorials. For learning:

```bash
minikube config set cpus 4
minikube config set memory 8192        # 8 GiB
minikube config set disk-size 20000    # 20 GB
```

These persist as defaults for every subsequent `minikube start`. Raising the floor after a cluster exists requires `minikube delete && minikube start` — set it first.

**Enable the learning-essential addons on first `start` or immediately after:**

```bash
minikube addons enable ingress
minikube addons enable metrics-server
minikube addons enable dashboard         # optional but useful for learners
```

Do not enable `registry`, `csi-hostpath-driver`, or `olm` by default — they add resource load and are only needed for specific tutorials.

**Verify the cluster is reachable before claiming setup is done:**

```bash
kubectl cluster-info                      # should print control-plane + CoreDNS URLs
kubectl get nodes                         # should show at least one Ready node
kubectl config current-context            # should be "minikube" (or active profile name)
```

Any of these failing is a hard-stop — do not proceed to tutorials until all three pass.

### macOS-specific access-path quirks (teach these upfront)

These are the three gotchas that trip every macOS learner using the `docker` driver. Mention them before the user hits them:

1. **`type: LoadBalancer` stays `<pending>` forever.** Minikube has no cloud load balancer. The fix is a separate terminal running `minikube tunnel` (needs sudo). This is expected, not a bug.
2. **NodePort at `localhost:3xxxx` doesn't work with the `docker` driver.** The "node" is inside the Docker VM, not on the host. Use `minikube service <svc> --url` which opens a tunnel through, or `kubectl port-forward svc/<name> 8080:80`.
3. **Local-built Docker images are not visible to the cluster.** Either `minikube image load <image:tag>`, or `eval $(minikube docker-env)` before `docker build` so the image lands in the cluster VM's Docker daemon directly.

**When reviewing a tutorial or script**, apply `rules/findings-format.md`'s three buckets:
- **Must Fix**: `minikube start` command without `--driver` on a host where the default would fail (Apple Silicon + no Docker Desktop); a tutorial that uses `type: LoadBalancer` without naming the `minikube tunnel` requirement; a step that creates a local-build image and `kubectl apply`s it with no `minikube image load` or `docker-env` step
- **Should Fix**: resource floor not set before first `start` (will manifest as metrics-server crash looping later); essential addons not enabled before the tutorial that needs them; access-path quirk not called out at the point it matters
- **Consider**: using the dashboard addon as a visualization aid for a learner; naming the exact context (`kubectl config current-context`) before destructive commands

## Pragmatism Guard

Do not apply this rule when:

- **The user is on a managed cluster** (EKS/GKE/AKS/Rancher/Docker Desktop Kubernetes) rather than minikube. Driver choice, local addons, and the macOS access-path quirks don't apply — defer to the managed cluster's docs.
- **Running inside a container image or dev container** that already declares `kubectl` + `minikube` + Docker — trust the image; do not re-install.
- **The user has explicitly said their local environment is set up.** Skip the check; if a command then fails on a missing-dependency signal, run the check at that point.
- **`kind` or `k3d` is the local tool of choice instead of minikube.** The driver and addon advice does not apply; the kubectl install does. Point to the kind/k3d docs for the rest.

## Anti-Patterns to Avoid

- **Running `minikube start` with no resource config and hoping metrics-server comes up.** It won't — the control-plane plus a serving app plus metrics-server does not fit in 2 GiB. Set the floor first.
- **Blindly enabling every addon.** Each enabled addon adds a Pod to the control plane and competes for the resource floor. Enable only what the current tutorial needs.
- **`sudo` as the fix for a permission problem on Linux.** If `docker info` requires sudo, the user is not in the `docker` group — fix the group membership, don't carry sudo through every subsequent command.
- **"Just use `kubectl` from Docker Desktop's bundled Kubernetes."** Docker Desktop's K8s and minikube both write to `~/.kube/config` and both call their context names things that resemble each other. Learners end up applying to the wrong cluster. Pick one; `kubectl config get-contexts` is non-negotiable before destructive commands.
- **Suggesting `virtualbox` or `hyperkit` as the driver.** Both are either broken on current Apple Silicon or deprecated upstream. Default to `docker`; fall back to `qemu` on M-series without Docker Desktop.
