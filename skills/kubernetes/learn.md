# Kubernetes Learning Guide

Concept index for someone new to Kubernetes who is running minikube locally. Each section is self-contained — read linearly for a full learning path, or jump to a specific topic.

Target reader: a developer who has used Docker, understands HTTP services, and wants to go from zero to deploying a small app on a local cluster without first swallowing a 400-page book. Everything here is checked against the live Kubernetes docs; nothing is written to be impressive.

---

## 0. Why this exists (and when to skip it)

Kubernetes is an orchestrator for *containers*. If you already run your app as one Docker image, Kubernetes gives you: multiple replicas, automatic restart, declarative config in Git, rolling updates, a stable internal DNS name per service, and the same manifests working on a laptop and in production.

The cost: a lot of jargon, a lot of yes-you-really-do-need-this-field YAML, and a cluster that fails in ways `kubectl apply` happily accepts without complaint.

Skip this guide if you only need: a single container running, no replicas, no production. Use `docker run` or `docker compose`. Come back when any of those stops being enough.

---

## 1. The cluster — what's actually running

A **cluster** is a control plane plus one or more worker nodes. On minikube with the `docker` driver, the entire cluster is a single Docker container pretending to be a VM; from inside, it looks like a real Linux host.

- **Control plane components** (you rarely touch these directly):
  - `kube-apiserver` — the REST API; `kubectl` talks to this
  - `etcd` — the cluster's state store (think: a tiny database holding every manifest you've applied)
  - `kube-scheduler` — picks which node a Pod runs on
  - `kube-controller-manager` — runs the reconciliation loops (Deployment → ReplicaSet → Pod, etc.)
- **Node components** (one of each per worker node):
  - `kubelet` — the agent that actually runs containers on this node
  - `kube-proxy` — writes iptables rules so Services have working virtual IPs
  - A container runtime (containerd on minikube)

**The mental model**: you describe desired state in YAML → `kubectl apply` writes it to etcd via the apiserver → controllers notice the gap between actual and desired → kubelets on each node pull images and run containers to close it. Everything you do is modifying desired state. The cluster converges.

**Try it:**

```bash
kubectl get componentstatuses             # control-plane health
kubectl get nodes                         # expect "Ready"
kubectl get pods -n kube-system           # the control plane running as Pods
```

---

## 2. Pods — the smallest unit

A **Pod** is one or more containers that share a network namespace (same IP and ports) and can share volumes. Almost always one container per Pod; sidecars (logging agents, service mesh proxies) are the exception.

**You rarely create Pods directly.** A bare `kind: Pod` has no auto-restart on node failure. You create a *controller* (Deployment, StatefulSet, etc.) that owns Pods.

**Pod lifecycle phases**:

- `Pending` — accepted by the apiserver but not yet running (waiting for scheduling, image pull, volume mount)
- `Running` — at least one container is running
- `Succeeded` — all containers exited with code 0 (Jobs end here)
- `Failed` — at least one container exited with non-zero
- `Unknown` — the node is unreachable

The real debugging signals come from the Pod's **container states**: `Waiting` (with reasons like `ImagePullBackOff`, `CrashLoopBackOff`), `Running`, `Terminated` (with exit code + reason, e.g. `OOMKilled`).

**Try it:**

```bash
kubectl run tmp --image=nginx --restart=Never    # creates a bare Pod (NOT how to deploy real apps)
kubectl get pod tmp -o wide
kubectl describe pod tmp
kubectl delete pod tmp
```

---

## 3. Deployment — the default controller

A **Deployment** manages a `ReplicaSet` which manages Pods. It gives you:

- A fixed number of replicas (`replicas: 3`)
- Rolling updates (new ReplicaSet scales up as old scales down)
- Automatic rollback (`kubectl rollout undo`)
- A template defining the Pod spec

**Minimal Deployment**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hello
spec:
  replicas: 2
  selector:
    matchLabels: { app: hello }
  template:
    metadata:
      labels: { app: hello }
    spec:
      containers:
        - name: app
          image: kicbase/echo-server:1.0
          ports: [{ name: http, containerPort: 8080 }]
```

**The three-way label match** — the single most common beginner failure:

- `spec.template.metadata.labels` → labels that go on each Pod (e.g. `app: hello`)
- `spec.selector.matchLabels` → which Pods this Deployment owns (must be a subset of template labels)
- Any Service that targets these Pods will also need a `selector` matching the template labels

A typo in one of the three → the Service matches zero Pods → "connection refused" with no `kubectl` error.

**Try it:**

```bash
kubectl apply -f deployment.yaml
kubectl get deployment hello
kubectl get pods -l app=hello
kubectl rollout status deployment/hello
```

---

## 4. Services — stable network identity

Pods come and go (restarts, scale-ups, rolling updates) and get fresh IPs each time. A **Service** gives you a stable DNS name and virtual IP that routes to whichever Pods currently match its selector.

**Service types:**

| Type | Reachable from | Use when |
|---|---|---|
| `ClusterIP` (default) | Inside the cluster | Internal-only services (microservices talking to each other) |
| `NodePort` | Node's IP + port 30000–32767 | You need external access but no cloud LB |
| `LoadBalancer` | Public IP (cloud provider provisioned) | Production in cloud |
| `ExternalName` | Returns a CNAME | Pointing at an external DNS name |

**On minikube** `LoadBalancer` stays `<pending>` forever unless you run `minikube tunnel` in a separate terminal. This is expected; it's a local-cluster limitation.

**Minimal Service to go with the Deployment above:**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: hello
spec:
  selector: { app: hello }           # must match Pod labels
  ports:
    - port: 80                        # the Service port
      targetPort: http                # named port on the Pod (preferred over a number)
  type: ClusterIP
```

**Debug Service connectivity:**

```bash
kubectl get svc hello
kubectl get endpoints hello     # if empty → selector doesn't match any Pods
kubectl describe svc hello
kubectl port-forward svc/hello 8080:80    # tunnel from your laptop to the cluster
```

Once port-forwarded, `curl localhost:8080` reaches a Pod via the Service.

---

## 5. ConfigMap and Secret — decoupling config from image

Non-secret config (feature flags, URLs, log levels) belongs in a **ConfigMap**. Sensitive values (passwords, tokens, keys) belong in a **Secret**.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: hello-config
data:
  GREETING: "hello from kubernetes"
  LOG_LEVEL: "info"
```

Consume in a Pod:

```yaml
# as env vars
envFrom:
  - configMapRef: { name: hello-config }

# or as mounted files
volumes:
  - name: config
    configMap: { name: hello-config }
volumeMounts:
  - name: config
    mountPath: /etc/config
```

**Secrets are not encrypted** — they're base64-encoded. Treat them as "mildly obfuscated" unless the cluster has encryption-at-rest configured. **Never commit real Secret values to Git.** Use external secret managers (sealed-secrets, external-secrets, SOPS) or create them out-of-band:

```bash
kubectl create secret generic hello-secret --from-literal=API_KEY=xxx
```

**Secret consumption via volume mount is safer than env vars** — env vars leak via `/proc/<pid>/environ` and crash dumps. Only use env-var consumption when the library insists on it.

**ConfigMap updates don't auto-restart Pods using env vars** — the Pod sees the old value until it restarts. For volume-mounted consumption, the kubelet eventually updates the file (with sync delay). To force a rollout on config change: annotate the Pod template with a checksum of the ConfigMap, so changing the ConfigMap changes the annotation changes the template changes the rollout.

---

## 6. Resources and probes — reliability

**Resources** tell the scheduler what your Pod needs and limit what it can take:

```yaml
resources:
  requests:
    cpu: 50m            # 0.05 of a CPU core — what you need to be scheduled
    memory: 64Mi        # what you need to be guaranteed
  limits:
    memory: 128Mi       # kill the container if it exceeds this
    # cpu limit is often omitted for latency-sensitive services (CFS throttling)
```

A container with no `requests` is unschedulable in any serious sense (the scheduler assumes 0 and lands it anywhere, where it gets evicted first under pressure). A container with no `limits.memory` can grow unbounded and starve its neighbors.

**Probes** let the kubelet know your app's health:

- **readinessProbe** — "should traffic flow to this Pod?" If it fails, the Pod is removed from Service endpoints but not killed.
- **livenessProbe** — "is this process stuck?" If it fails, the container is restarted.
- **startupProbe** — "has startup finished?" Lets you set generous liveness/readiness timings for a slow boot without weakening them forever.

```yaml
readinessProbe:
  httpGet: { path: /ready, port: http }
livenessProbe:
  httpGet: { path: /live, port: http }
  initialDelaySeconds: 10
```

**Keep probes shallow.** A readiness probe that hits the DB couples every Pod's readiness to the DB — a transient blip becomes an outage. Probe the process; report dependency health through app metrics.

---

## 7. Namespaces, labels, and selectors

A **namespace** is a scope for names and a boundary for RBAC and quotas. Create one per logical app family or environment:

```bash
kubectl create namespace demo
kubectl config set-context --current --namespace=demo
```

**Labels** (`key: value`) attach metadata to any resource — Pods, Services, Nodes. **Selectors** query by label (`-l app=hello,env=prod`). This is how Services find Pods, how `kubectl get -l` filters, and how NetworkPolicies target traffic.

Standard recommended labels (tools like Lens and Argo CD read these):

```yaml
app.kubernetes.io/name: hello
app.kubernetes.io/instance: hello-prod
app.kubernetes.io/version: "1.2.3"
app.kubernetes.io/component: frontend
app.kubernetes.io/part-of: shop
app.kubernetes.io/managed-by: kubectl
```

---

## 8. Storage — Volumes, PV, PVC

Containers are ephemeral; their filesystems vanish on restart. **Volumes** persist data for the Pod's lifetime; **PersistentVolumes** persist across Pod restarts.

- `emptyDir` — scratch space; dies with the Pod. Fine for cache dirs.
- `configMap` / `secret` — mount a ConfigMap/Secret as files.
- `persistentVolumeClaim` — the Pod's *request* for storage; the cluster binds it to a PersistentVolume.
- `hostPath` — mounts a path from the node's filesystem. Dev-only on minikube; a security risk in production.

**Access modes:**

- `ReadWriteOnce` (RWO) — one node can mount it read-write
- `ReadOnlyMany` (ROX) — many nodes can mount it read-only
- `ReadWriteMany` (RWX) — many nodes can mount it read-write (rare without a networked FS like NFS)

On minikube, the default `StorageClass` is `standard` and uses the `hostpath` provisioner — PVCs bind to a path on the minikube node. Good enough for learning; useless for production.

---

## 9. StatefulSets, DaemonSets, Jobs, CronJobs

Deployment is the default. The others are narrower patterns:

- **StatefulSet** — Pods have stable identity (`name-0`, `name-1`, ...) and stable per-Pod PVCs. Use when each replica is different (databases, Kafka brokers).
- **DaemonSet** — one Pod per node. Use for log shippers, node exporters, CNI/CSI drivers.
- **Job** — run-to-completion. Set `backoffLimit` and `activeDeadlineSeconds` or you'll have a Job retrying forever.
- **CronJob** — Jobs on a schedule. Set `spec.timeZone` on K8s 1.27+ or your schedule is implicitly in the cluster's local time.

---

## 10. RBAC and ServiceAccounts

Every Pod runs as a **ServiceAccount** (SA). The SA is how in-cluster code authenticates to the apiserver. By default:

- Pods use the namespace's `default` SA
- The SA's token is mounted into the Pod at `/var/run/secrets/kubernetes.io/serviceaccount/token`

For an app that doesn't call the Kubernetes API, set `automountServiceAccountToken: false` on the Pod spec — the mounted token is a privilege-escalation surface.

For an app that *does* call the API (operators, controllers, apps using the downward API): create a dedicated SA, a `Role` enumerating the verbs and resources it needs, and a `RoleBinding` binding the SA to the Role in that namespace.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: hello-reader
  namespace: demo
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "list", "watch"]
```

**Never** grant `cluster-admin` to an application SA. **Never** use `verbs: ["*"]` or `resources: ["*"]` — that's a signal you don't know what you need. Figure out exactly what the app calls (`kubectl auth can-i --as=system:serviceaccount:demo:hello`).

---

## 11. Pod Security Standards

Three profiles, enforced at the namespace level via labels:

- `privileged` — no restrictions
- `baseline` — prevents known escalations (no `hostNetwork`, no `privileged: true`, no `hostPath`)
- `restricted` — hardened defaults (`runAsNonRoot`, `readOnlyRootFilesystem`, drop all capabilities)

For a learning namespace, apply `baseline`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: demo
  labels:
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/enforce-version: latest
```

For greenfield production apps, start with `restricted` — it forces habits (non-root UIDs, readonly roots, dropped capabilities) that are much harder to add retroactively.

---

## 12. The learning path (what to do in what order)

1. **Install the toolchain** → `/kubernetes setup`, then `/kubernetes start`. Confirm `kubectl cluster-info` + `kubectl get nodes` pass.
2. **Inspection vocabulary** → `get`, `describe`, `logs`, `events`, `explain`, `api-resources`. No creating yet. Spend 15 minutes just poking at the control plane.
3. **Run the hello-app fixture** → `/kubernetes apply skills/kubernetes/examples/hello-app/01-good` applies a correctly-wired Deployment + Service. Confirm Pods go Ready, endpoints populate, and `curl` through `port-forward` returns a response. Then `02-broken-selector` and `03-missing-probe` as structured failures with their own `/kubernetes debug` loops — see `skills/kubernetes/examples/hello-app/README.md`.
4. **First hand-authored workload** → `kubectl create deployment hello --image=nginx`, then `kubectl expose deployment hello --port=80`. Convert both to YAML with `-o yaml --dry-run=client`. This is the imperative-to-declarative transition.
5. **Services and reachability** → ClusterIP + `port-forward`, then NodePort (teach the minikube quirk), then LoadBalancer with `minikube tunnel`.
6. **ConfigMap and Secret** → env vs volume mount tradeoffs; the config-change rollout gotcha.
7. **Rollouts and rollbacks** → `kubectl set image`, `rollout status`, `rollout undo`. Watch ReplicaSets scale.
8. **Resources and probes** → set requests/limits; deliberately set a limit too low to see OOMKilled; deliberately break a readiness probe to see traffic get withdrawn.
9. **Storage** → emptyDir → PVC with `standard` StorageClass → StatefulSet.
10. **Networking depth** → cluster DNS (`<svc>.<ns>.svc.cluster.local`), headless Services, Ingress addon.
11. **Debugging drills** → deliberately break something from the symptom table in `k8s-debugger`; practice the first-command loop (the fixture's `02-broken-selector` and `03-missing-probe` are starting points).
12. **Security** → ServiceAccount, Role, RoleBinding; Pod Security `baseline`.
13. **Workload variety** → Jobs, CronJobs, DaemonSets, StatefulSets as narrower patterns off the Deployment foundation.

Keep the `cheatsheet` next to your terminal. The ability to go from symptom to first command without thinking is the single highest-leverage skill a learner builds.
