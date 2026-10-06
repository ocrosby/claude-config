---
name: k8s-conventions
description: Kubernetes manifest and cluster-shape conventions — workload picks, Service/selector hygiene, ConfigMap/Secret usage, resource requests, probes, RBAC, Pod Security. Applies to any `.yaml` under `k8s/`, `manifests/`, `deploy/`, `charts/`, or `kustomize/`.
type: rule
paths:
  - "**/k8s/**/*.yaml"
  - "**/k8s/**/*.yml"
  - "**/manifests/**/*.yaml"
  - "**/manifests/**/*.yml"
  - "**/deploy/**/*.yaml"
  - "**/deploy/**/*.yml"
  - "**/charts/**/*.yaml"
  - "**/kustomize/**/*.yaml"
---

# Kubernetes Application Conventions

Kubernetes failures almost never surface at the line that caused them. A missing `resources.requests.memory` doesn't fail at apply — it fails three days later when a Pod OOMKills under load. A Deployment-Service label mismatch produces a 200-OK apply and an empty EndpointSlice. The conventions below exist because the apiserver accepts almost anything and the real validation is "it survives contact with a running cluster."

For local-development setup (minikube, drivers, resource floors, image loading) see `rules/minikube-setup.md` — this rule does not repeat it. For general security crosscuts (RBAC, Pod Security, secret handling) `rules/owasp-top-10.md` applies on top of this rule, especially A01, A02, A05, A08.

## Standard manifest layout

```
<repo>/
├── k8s/                       -- declarative manifests, one dir per app
│   └── <app>/
│       ├── deployment.yaml
│       ├── service.yaml
│       ├── configmap.yaml
│       ├── kustomization.yaml    -- optional: kustomize overlays
│       └── overlays/
│           ├── local/
│           └── prod/
└── <app source code>/
```

One kind per file. Co-locate the Deployment and its Service — they refer to each other by label; splitting them across directories is a recognized source of selector drift.

## Recognition Signals

### Workloads — picking the right controller

| Signal | Convention |
|---|---|
| Bare `kind: Pod` outside a test fixture or one-shot debug session | A Pod with no controller is not restarted on node failure. Wrap in a `Deployment` (stateless), `StatefulSet` (stable identity), `DaemonSet` (one per node), or `Job`/`CronJob` (run-to-completion) |
| `StatefulSet` chosen for a stateless app because "it has persistent storage" | A stateless app with a PVC should still be a `Deployment` with `volumeClaimTemplates` is a StatefulSet-only feature — but only use StatefulSet when stable pod identity (`-0`, `-1`) is needed. The pod identity is the point, not the storage |
| `replicas: 1` on a Deployment serving user traffic without `maxUnavailable: 0` on the strategy | During a rollout, the single Pod is replaced in-place → brief downtime. Either `replicas: 2+` or `strategy.rollingUpdate.maxUnavailable: 0` with `maxSurge: 1` |
| Deployment and a `HorizontalPodAutoscaler` targeting it, but `replicas` set in the Deployment manifest | HPA fights the manifest on every apply. Omit `replicas` on Deployments managed by HPA |
| `Job` without `backoffLimit` and `activeDeadlineSeconds` | A failing Job retries forever by default (`backoffLimit: 6` then stuck). Set both explicitly |
| `CronJob` with timezone-sensitive schedule and no `timeZone` field | `spec.timeZone` (K8s 1.27+) makes schedule intent explicit — otherwise the cluster's local time is implicit and non-portable |

### Services, selectors, labels

| Signal | Convention |
|---|---|
| Deployment Pod labels and Service `selector` not identical (missing a key, extra key, typo) | Service matches zero Pods → empty `EndpointSlice` → "connection refused" from inside the cluster. `kubectl get endpoints <svc>` is the diagnostic |
| `Service.spec.selector` keys that are not also in the Deployment's `spec.template.metadata.labels` | Same failure mode — missing label on the Pod template → no match |
| `Service.ports[].targetPort` is a number but the Pod container exposes a *different* number | Service routes to the targetPort number regardless of container port. Prefer naming the port in the container (`ports: [{name: http, containerPort: 8080}]`) and referencing it by name in the Service (`targetPort: http`) — rename-safe |
| `type: LoadBalancer` in a manifest that will also run on minikube/kind | Local clusters have no cloud LB — `EXTERNAL-IP` stays `<pending>`. Either use `ClusterIP` + `kubectl port-forward` locally, or `minikube tunnel` as a known workaround |
| Ingress referenced in docs but no `ingressClassName` set on the Ingress resource | K8s 1.22+ requires an explicit `ingressClassName`; `kubernetes.io/ingress.class` annotation is deprecated |
| No `app.kubernetes.io/name`, `app.kubernetes.io/instance`, or `app.kubernetes.io/version` labels | Standard recommended labels — tools like `kubectl`, Lens, Argo CD expect them for grouping. Not a correctness issue but a discoverability one |

### Config and Secrets

| Signal | Convention |
|---|---|
| Non-secret config (feature flags, URLs, log levels) baked into the container image | Non-secret config belongs in a `ConfigMap`, consumed via `envFrom` or a volume mount — a config change should not require a new image build |
| Secret value inline in a committed manifest (`stringData: PASSWORD: hunter2`) | Secrets in Git are compromised regardless of the repo's visibility. Use `kubectl create secret ... --dry-run=client -o yaml` out-of-band, or external secret managers (sealed-secrets, external-secrets, SOPS). `rules/owasp-top-10.md` A08 |
| `ConfigMap` used to hold a value that is actually sensitive (API token, DB password, signing key) | ConfigMaps are not RBAC-protected the same way Secrets are, and they appear in logs/describe output. Move to a `Secret` |
| `Secret` consumed via `env` instead of a file-mounted volume | Env vars leak to child processes, `/proc/<pid>/environ`, and crash dumps. Volume-mounted secrets are the safer default; `env`-mounted is acceptable only when the consuming library insists on it |
| ConfigMap or Secret changed but the Pod not restarted | Env-var consumption does NOT auto-reload; volume-mount consumption does (eventually, with cache delay). Either annotate the Pod template with the config checksum to force a rollout (`checksum/config: {{ include ... }}`), or rely on volume mounts |

### Resources, probes, and reliability

| Signal | Convention |
|---|---|
| Container with no `resources.requests` | Scheduler assumes 0 — Pod lands on any node, risks eviction under pressure. Set `requests.cpu` and `requests.memory` on every container |
| Container with `requests` but no `limits` | Pod can grow unbounded on a shared node. Set `limits` explicitly; `limits.memory` is especially important — exceeding it = OOMKilled, which is a signal (bug or wrong limit), not an outage |
| `limits.cpu` set but the workload is latency-sensitive | CPU limits throttle (CFS quota), causing tail-latency spikes. For latency-sensitive services, set `requests.cpu` to the expected steady-state and omit `limits.cpu` (allow burst); for batch, cap both |
| No `readinessProbe` on a container serving traffic | Pod is added to Service endpoints the moment the container starts — before the app is ready → 502s during rollout. Add an HTTP or TCP readinessProbe |
| `livenessProbe` identical to `readinessProbe` | Different purposes: readiness controls traffic routing, liveness restarts the container. A liveness probe that fails during warmup causes a crash loop; readiness just delays traffic. Use a `startupProbe` for slow-starting apps instead of loosening liveness |
| `livenessProbe` with no `initialDelaySeconds` or `failureThreshold`, calling a heavy endpoint | Probes that call `/health` + hit the DB cause probe-induced crash loops. Keep probes shallow (process-liveness only); use the app's own health endpoint intentionally |

### Security defaults

| Signal | Convention |
|---|---|
| Container runs as root (no `securityContext.runAsNonRoot: true` or `runAsUser`) | Default is to run as whatever UID the image sets, often root. Set `securityContext.runAsNonRoot: true` and `runAsUser: <non-zero>` at Pod or container level |
| `securityContext.allowPrivilegeEscalation` unset (defaults to true) | Set `false` explicitly on every container — this is a Pod Security `baseline` requirement |
| `securityContext.readOnlyRootFilesystem` unset | Default allows writing anywhere in the container. Set `true` and mount an `emptyDir` for genuinely-writable paths (`/tmp`, cache dirs) |
| `hostNetwork: true`, `hostPID: true`, `hostIPC: true`, or `hostPath` volumes on anything but a DaemonSet logging agent | Pod shares host namespace / can read host files — breaks the Pod isolation boundary. These are Pod Security `privileged` territory; require a documented justification |
| `automountServiceAccountToken: true` (the default) on a Pod that never calls the Kubernetes API | Mounted token = any code in the Pod can impersonate the ServiceAccount. Set `automountServiceAccountToken: false` on the Pod spec or the ServiceAccount itself unless the app actually calls `kubectl`/the API |
| Workload uses the `default` ServiceAccount in the namespace | Create a dedicated ServiceAccount per workload (`sa.yaml`) so RBAC grants are per-app, not shared. `rules/owasp-top-10.md` A01 |
| Namespace has no `pod-security.kubernetes.io/enforce` label | Enforce at least `baseline` on application namespaces: `pod-security.kubernetes.io/enforce=baseline`. Use `restricted` for new greenfield apps |

### RBAC

| Signal | Convention |
|---|---|
| `ClusterRoleBinding` to `cluster-admin` for an application ServiceAccount | Almost always wrong — the app needs a narrow `Role` + `RoleBinding` scoped to its namespace |
| `verbs: ["*"]` or `resources: ["*"]` in a Role | Enumerate verbs (`get`, `list`, `watch`) and resources explicitly. `*` is a signal the author didn't know which permissions were actually needed |
| `apiGroups: [""]` with resource `secrets` in a workload Role | Granting an app read access to Secrets in its namespace is a security decision — flag for explicit confirmation; prefer mounting the specific Secret into the Pod instead |

### Images

| Signal | Convention |
|---|---|
| `image: myapp:latest` or any mutable tag | `latest` makes rollbacks ambiguous — the same tag can resolve to different digests over time. Pin by digest (`myapp@sha256:...`) or an immutable tag |
| `imagePullPolicy: Always` with a pinned tag | Default is fine (`IfNotPresent` for pinned tags, `Always` for `latest`). Explicit `Always` on a pinned tag is wasteful on image pulls |
| No `imagePullSecrets` on a Deployment pulling from a private registry | Pods will fail with `ImagePullBackOff`. Create a `docker-registry` Secret and reference it, OR grant it to the ServiceAccount |

## Mandatory Behaviors

**Design the Service, Deployment, and labels together.** The three must agree:
- Deployment `spec.selector.matchLabels` ⊆ Deployment `spec.template.metadata.labels`
- Service `spec.selector` ⊆ Deployment `spec.template.metadata.labels`
- When editing one of the three, verify the other two before applying.

**Every container has `resources.requests` for CPU and memory, and `resources.limits.memory` at minimum.** A container with no requests is unschedulable in any clustered sense and will be the first evicted under pressure.

**Every container serving traffic has a `readinessProbe`.** A `livenessProbe` is optional and must be shallower than readiness when present. Add a `startupProbe` instead of loosening liveness for slow-starting apps.

**Never commit a Secret with real values to Git.** Even in a private repo. Use external secret management or dry-run manifests generated out-of-band.

**Pin images by digest or an immutable tag.** `latest` is a bug.

**When reviewing manifests**, apply `rules/findings-format.md`'s three buckets. Must Fix items are further split into two tiers — the split matters for `/kubernetes apply`, which hard-blocks on apply-blocking Must Fix items and only displays always-flagged ones. The reviewer still reports both tiers under the same **Must Fix** heading.

- **Must Fix (apply-blocking)** — manifest is destructive or structurally broken: Deployment/Service selector mismatch; real secret value committed to Git; `cluster-admin` grant to an application ServiceAccount; `hostNetwork`/`hostPath` without documented justification.
- **Must Fix (always-flagged, non-blocking for apply)** — habit-forming correctness issues that fire on nearly every tutorial manifest and shouldn't stop a learner from running their first apply: `kind: Pod` without a controller; `image: *:latest`; namespace without a Pod Security enforce label on anything beyond `kube-system`.
- **Should Fix**: missing `resources.requests` or `limits.memory`; missing `readinessProbe` on a traffic-serving container; identical liveness and readiness probes; `automountServiceAccountToken` unset on Pods that don't call the API; shared `default` ServiceAccount
- **Consider**: missing recommended labels (`app.kubernetes.io/name` etc.); `targetPort` as a number instead of a named port; `limits.cpu` on a latency-sensitive service

## Pragmatism Guard

Do not apply this rule when:

- **The manifest is a disposable test fixture or a `kubectl run` one-liner** for debugging — a bare Pod spun up to curl another Pod is correct for that purpose.
- **The repo is a chart/kustomize library** whose job is to emit skeletons for others to parametrize — in that case the rule applies to the rendered output, not the templates (which deliberately leave some fields unset for the consumer to fill in).
- **A specific field is deliberately left to a kustomize overlay or Helm value** — flag that the convention is enforced in the overlay, not the base.

## Anti-Patterns to Avoid

- **"It applied, so it works."** `kubectl apply` validates syntax, not behavior. A manifest that applies cleanly can still produce zero endpoints, a crash loop, or an OOMKill — the `apply` success message is not evidence of correctness.
- **Copying a Deployment from one app to another and forgetting to change every label.** The old `app:` label stays and the new Service's selector matches both apps' Pods — silent cross-wiring. Grep every label value against the app name before applying.
- **Granting `cluster-admin` "temporarily" to fix a permissions problem.** The grant never gets removed. Debug with `kubectl auth can-i --as=system:serviceaccount:<ns>:<sa>` instead.
- **Reaching for `latest` because "we always deploy the newest."** You still want a specific digest in the manifest — the CD pipeline updates the manifest with the new digest; the manifest is authoritative, not the registry's `latest` pointer.
