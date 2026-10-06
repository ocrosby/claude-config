---
description: Use when the user asks to learn Kubernetes, start/manage a local minikube cluster, scaffold or review Kubernetes manifests, or debug a cluster/Pod/Service issue. Invoke as /kubernetes <learn|setup|start|stop|status|design|apply|review|debug|cheatsheet>.
argument-hint: "<subcommand> [arguments]"
arguments: [subcommand]
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---

# Kubernetes: Local Learning + Dispatch

Use this skill whenever Kubernetes is in play — learning the concepts, running minikube locally, designing manifests, reviewing manifests, or debugging a cluster or workload. Delegates architecture to `k8s-architect`, review to `k8s-reviewer`, and debugging to `k8s-debugger`. Prerequisite install is governed by `rules/minikube-setup.md`; manifest/security conventions by `rules/k8s-conventions.md` — this skill orchestrates, it does not restate either.

## When NOT to use

- The user is working against a managed cluster (EKS/GKE/AKS) and the question is about cloud-provider integration (IAM roles for service accounts, LB annotations) rather than Kubernetes itself → defer to the cloud provider's docs; this skill's minikube bias will mislead.
- Helm chart authoring beyond `values.yaml` review (template language, library charts) → outside this skill's scope.
- The user has explicitly requested a different local tool (`kind`, `k3d`, Docker Desktop Kubernetes) → honor the explicit choice; most subcommands still apply but `start`/`stop`/`status` are minikube-specific.

## Usage

```
/kubernetes                        # show this help
/kubernetes learn [topic]           # open the concept index; optionally jump to a topic
/kubernetes setup                   # check/install kubectl + minikube prerequisites
/kubernetes start                   # start minikube with the recommended resource floor + addons
/kubernetes stop                    # stop the active minikube cluster
/kubernetes status                  # cluster + node + context health check
/kubernetes design [description]    # invoke k8s-architect for a new app or restructure
/kubernetes apply <path>            # pre-flight review + kubectl apply + verify endpoints
/kubernetes review [paths]          # invoke k8s-reviewer on the given manifests (defaults to git diff)
/kubernetes debug <description>     # invoke k8s-debugger on a Pod/Service/rollout failure
/kubernetes cheatsheet              # print the kubectl + minikube cheatsheet
```

## Workflow

### 1. Parse the subcommand

Split `$ARGUMENTS` on the first space. The first word is the subcommand.

- Empty or `help` → print **Usage** and stop.
- Not one of `learn`, `setup`, `start`, `stop`, `status`, `design`, `apply`, `review`, `debug`, `cheatsheet` → print **Usage** and stop.
- Dispatch to the matching step.

### 2. Dispatch — `learn`

Must read `~/.claude/skills/kubernetes/learn.md` and present the concept index. If the user named a topic after `learn`, scroll to that topic and present only its section. Learning content is Level 3 — the skill does not duplicate it inline.

### 3. Dispatch — `setup`

Must run the prerequisite check:

```bash
bash ~/.claude/skills/kubernetes/check_prereqs.sh
```

If it exits `1`, present the gaps and their install commands from `rules/minikube-setup.md`. **If any gap requires `sudo` or `brew install`/`winget install`: stop and get explicit confirmation before running it.** Version checks and user-scoped installs do not require this extra confirmation pass.

### 4. Dispatch — `start`

1. Must run the prerequisite check (step 3) first. **If any prerequisite is missing: stop and surface the gaps.** Do not attempt `minikube start` with incomplete prereqs.
2. Must verify resource floor is set before first start:
   ```bash
   minikube config get cpus    # expect >= 4
   minikube config get memory  # expect >= 8192
   ```
   If unset or below the floor, must apply the recommended values from `rules/minikube-setup.md`:
   ```bash
   minikube config set cpus 4
   minikube config set memory 8192
   ```
3. Must detect the appropriate driver by reading the output of `check_prereqs.sh` (step 3) — the script prints the detected driver name on a line like `- docker: present and running` or `- qemu: present (Apple Silicon fallback)`. Pass it explicitly to minikube:
   ```bash
   # Capture the first available driver detected by check_prereqs.sh
   driver="$(bash ~/.claude/skills/kubernetes/check_prereqs.sh 2>/dev/null \
     | awk -F: '/^- (docker|qemu|kvm2|podman|hyperv): / { gsub(/^- /, "", $1); print $1; exit }')"
   minikube start --driver="${driver:-docker}"
   ```
   **If `driver` is empty: stop and surface that the prereq script detected no usable driver** — this means step 1 missed a gap.
4. Must enable learning-essential addons:
   ```bash
   minikube addons enable ingress
   minikube addons enable metrics-server
   ```
5. Must verify cluster reachability:
   ```bash
   kubectl cluster-info
   kubectl get nodes
   kubectl config current-context
   ```
   **If any of the three fail: stop and dispatch to `debug`.**

### 5. Dispatch — `stop`

Must run:

```bash
minikube stop
minikube status --format='{{.Host}}'
```

**If the status is not `Stopped`: stop and report the actual state** — a stop that silently fails leaves a cluster running and consuming resources.

### 6. Dispatch — `status`

Run and report, in parallel:

```bash
kubectl config current-context
minikube status
kubectl get nodes
kubectl get pods -A | head -20
```

Must flag any `NotReady` node, `CrashLoopBackOff` Pod, or context pointing somewhere other than the expected minikube cluster. If any surface, dispatch to `debug` with the specific symptom.

### 7. Dispatch — `design`

Invoke the `k8s-architect` agent. Must gather first: the app's purpose, workload lifecycle (long-running vs run-to-completion vs scheduled), state model (stateless vs per-replica identity), traffic shape (internal/external, HTTP/TCP), and target cluster (minikube only, managed, or both). Must present the agent's workload choice, label plan, Service shape, config/secret split, probe strategy, resource plan, and RBAC surface to the user. **If the user has not explicitly approved the design: stop and do not proceed to writing manifests.**

### 8. Dispatch — `apply`

**Precondition:** a path to one or more manifest files or a directory was given. **If missing: stop and ask.**

1. Must invoke `k8s-reviewer` on the paths first. **If any Must Fix findings: stop and present them.** Do not apply manifests with known Must Fix issues.
2. Run:
   ```bash
   kubectl apply -f <path> --dry-run=client
   ```
   **If dry-run fails: stop and report the error.** Do not proceed to a live apply.
3. Run the live apply:
   ```bash
   kubectl apply -f <path>
   ```
4. Must verify every created Deployment reaches `Available` and every Service has non-empty endpoints:
   ```bash
   kubectl rollout status deployment/<name> -n <ns>    # for each Deployment
   kubectl get endpoints -n <ns>                        # expect non-empty for every new Service
   ```
   If any Deployment stalls or any Service has empty endpoints, dispatch to `debug`.

### 9. Dispatch — `review`

**Identify scope.** If no path argument: `git diff --name-only HEAD`. Filter to files matching Kubernetes patterns (`apiVersion:` + a known `kind:`, a `kustomization.yaml`, or a `values.yaml`) — if none match, report that and stop (mirrors `k8s-reviewer`'s own precondition, checked here first to avoid an unnecessary agent call). Must exclude Helm template files (`charts/*/templates/*.yaml` and `Chart.yaml`) — Helm templating is out of scope per the "When NOT to use" section.

Invoke the `k8s-reviewer` agent on the matched files. Report its findings per `rules/findings-format.md`.

### 10. Dispatch — `debug`

**Precondition:** a description of the failure was given. **If missing: stop and ask** for the symptom (`kubectl` output or user description), the resource name, the namespace, and whether the target cluster is minikube or managed.

Invoke the `k8s-debugger` agent with the failure description and any available output. Report root cause, evidence, fix, and regression risk per `rules/debug-process.md`.

### 11. Dispatch — `cheatsheet`

Must read `~/.claude/skills/kubernetes/cheatsheet.md` and print it. Reference material is Level 3 — the skill does not duplicate commands inline.

### 12. Final verification step

- `learn` → the requested topic (or the index) was presented from `learn.md`
- `setup` → prerequisite check report delivered; gaps named with their install commands
- `start` → `kubectl cluster-info`, `get nodes`, and `current-context` all pass before reporting success
- `stop` → `minikube status` confirms stopped
- `status` → the four parallel reports were presented, any abnormal signal was flagged
- `design` → user has explicitly approved the proposal before any implementation starts
- `apply` → review passed with no Must Fix, dry-run passed, live apply succeeded, every rollout and endpoint verified
- `review` → findings reported per `rules/findings-format.md`, or the "no Kubernetes patterns" skip message if scope didn't match
- `debug` → report includes all four of root cause, evidence, fix, and regression risk
- `cheatsheet` → the cheatsheet was presented from `cheatsheet.md`

If any of the above is incomplete, do not report the subcommand as done.

## Rules (apply across all subcommands)

- `rules/minikube-setup.md` is authoritative for prerequisite detection, driver choice, resource floors, addons, and the macOS access-path quirks — do not restate its content here.
- `rules/k8s-conventions.md` is authoritative for manifest shape, labels, probes, resources, RBAC, and image hygiene — do not restate its checklist here.
- `design` never proceeds to writing manifests before the user has explicitly approved the proposal.
- `apply` is gated on a passing review and a passing dry-run; Must Fix findings are not overridable from this skill.
- **`disable-model-invocation` is deliberately unset.** `start` and `apply` have real side effects (starts a VM; applies manifests to a cluster), which would normally argue for it — but the whole point of this skill is that Claude auto-invokes it when Kubernetes is in play; blocking model invocation would silently defeat that. The side effects are instead gated inline: explicit confirmation before any `sudo`/system-wide install (step 3), explicit user approval before `design` proceeds, review-passes-before-apply (step 8). Do not add `disable-model-invocation: true` without re-confirming this trade-off with the user first.
