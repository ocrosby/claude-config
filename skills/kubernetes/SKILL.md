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

## Shared helper — context assertion (used by every destructive subcommand)

Every subcommand that mutates the cluster (`start`, `stop`, `apply`) or asserts cluster health as truth (`status`) must verify the active kubectl context matches the expected minikube cluster/profile **before** doing its work. The helper:

```bash
# Expected profile defaults to "minikube"; override with the active -p flag if the
# user passed one earlier in the session.
expected="${MINIKUBE_PROFILE:-minikube}"
actual="$(kubectl config current-context 2>/dev/null || echo '')"
if [ "$actual" != "$expected" ]; then
  echo "✗ kubectl context is '$actual', expected '$expected'."
  echo "  Switch with: kubectl config use-context $expected"
  echo "  Or if the cluster isn't running: /kubernetes start"
  exit 1
fi
```

**If the actual context does not equal the expected profile: stop and surface the switch command.** Do not proceed to the subcommand's work. The user may be targeting a different cluster deliberately — the fix is to switch context explicitly, not to override from inside this skill.

**Exception:** `start` runs this check *after* `minikube start` completes (because `minikube start` is itself what sets the context). All other destructive subcommands run the check **before** any cluster mutation.

## Workflow

### 1. Parse the subcommand

Split `$ARGUMENTS` on the first space. The first word is the subcommand.

- Empty or `help` → print **Usage** and stop.
- Not one of `learn`, `setup`, `start`, `stop`, `status`, `design`, `apply`, `review`, `debug`, `cheatsheet` → print **Usage** and stop.
- Dispatch to the matching step.

### 2. Dispatch — `learn`

Must read `~/.claude/skills/kubernetes/learn.md` and present the concept index. If the user named a topic after `learn`, scroll to that topic and present only its section. Learning content is Level 3 — the skill does not duplicate it inline.

**For hands-on practice** rather than reading, point the user at `skills/kubernetes/examples/hello-app/` — a three-tier working/broken-selector/missing-probe fixture. The intended loop is `/kubernetes apply skills/kubernetes/examples/hello-app/01-good` → observe success → `/kubernetes apply skills/kubernetes/examples/hello-app/02-broken-selector` → observe empty endpoints → `/kubernetes debug` on the symptom. See `skills/kubernetes/examples/hello-app/README.md`.

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
   ```
   **If either fails: stop and dispatch to `debug`.**
6. Must run the shared context assertion (see **Shared helper — context assertion** above) with `expected` set to the active profile. `minikube start` sets context to the started profile by default — if the assertion fails here, `minikube start` returned success but did not switch context (rare; usually a `--keep-context` config leak), and the user needs to run `kubectl config use-context $expected` manually.

### 5. Dispatch — `stop`

1. Must run the shared context assertion first — refuse to stop a cluster the user isn't currently targeting.
2. Then run:

```bash
minikube stop
minikube status --format='{{.Host}}'
```

**If the status is not `Stopped`: stop and report the actual state** — a stop that silently fails leaves a cluster running and consuming resources.

### 6. Dispatch — `status`

1. Must run the shared context assertion first — `status` reports cluster health as truth; reporting on the wrong cluster is a correctness defect.
2. Then run and report, in parallel:

```bash
kubectl config current-context
minikube status
kubectl get nodes
kubectl get pods -A | head -20
```

Must flag any `NotReady` node or `CrashLoopBackOff` Pod. If any surface, dispatch to `debug` with the specific symptom. (Context mismatch is already handled by the assertion in step 1.)

### 7. Dispatch — `design`

Invoke the `k8s-architect` agent. Must gather first: the app's purpose, workload lifecycle (long-running vs run-to-completion vs scheduled), state model (stateless vs per-replica identity), traffic shape (internal/external, HTTP/TCP), and target cluster (minikube only, managed, or both). Must present the agent's workload choice, label plan, Service shape, config/secret split, probe strategy, resource plan, and RBAC surface to the user. **If the user has not explicitly approved the design: stop and do not proceed to writing manifests.**

### 8. Dispatch — `apply`

**Precondition:** a path to one or more manifest files or a directory was given. **If missing: stop and ask.**

0. Must run the shared context assertion first — `kubectl apply` targets whichever cluster the current context names; refuse to apply unless the user is on the expected minikube cluster/profile.
1. Must invoke `k8s-reviewer` on the paths first. The reviewer labels every Must Fix finding as either **(apply-blocking)** or **(always-flagged)** per `rules/k8s-conventions.md`.
   - **If any apply-blocking Must Fix findings: stop and present them.** Do not apply manifests with destructive or structurally-broken issues (selector mismatch, real secret committed, cluster-admin grant, `hostNetwork`/`hostPath` without justification).
   - **If only always-flagged Must Fix findings (`:latest`, bare Pod, missing PSA label): display them prominently as warnings and proceed.** These are habit-forming learner traps, not apply-blockers — learners need to feel the real failure, not be stopped by a review gate.
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
- `start` → `kubectl cluster-info` and `get nodes` pass AND the context assertion matches the active profile before reporting success
- `stop` → context assertion passed before `minikube stop` ran, and `minikube status` confirms stopped
- `status` → context assertion passed before any report, the four parallel reports were presented, any abnormal signal was flagged
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
- `apply` is gated on a passing dry-run and no apply-blocking Must Fix findings. Always-flagged Must Fix items (`:latest`, bare Pod, missing PSA label per `rules/k8s-conventions.md`) are surfaced as warnings but do not block apply — the split exists so learners can run tutorial manifests through the skill without hitting a review wall.
- **`disable-model-invocation` is deliberately unset.** `start` and `apply` have real side effects (starts a VM; applies manifests to a cluster), which would normally argue for it — but the whole point of this skill is that Claude auto-invokes it when Kubernetes is in play; blocking model invocation would silently defeat that. The side effects are instead gated inline: explicit confirmation before any `sudo`/system-wide install (step 3), explicit user approval before `design` proceeds, review-passes-before-apply (step 8). Do not add `disable-model-invocation: true` without re-confirming this trade-off with the user first.
