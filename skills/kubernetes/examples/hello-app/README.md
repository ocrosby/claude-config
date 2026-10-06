# hello-app — Three-Tier Learner Fixture

A deliberately-small Kubernetes app in three variants. Apply each to your minikube cluster, observe the outcome, and use `/kubernetes debug` on the ones that fail. The failures are structured so the symptom table in `k8s-debugger` applies directly.

Each variant is a complete, applyable manifest set — Namespace + ConfigMap + Deployment + Service — in a single file. No kustomize, no Helm, no overlays. You can `kubectl diff -f` between tiers to see the exact one-line change that produces each failure mode.

## The three tiers

| Tier | What it demonstrates | Expected outcome |
|---|---|---|
| `01-good/` | A correctly-wired Deployment + Service with matching labels, named ports, resource requests, and a readiness probe | Pods reach Ready; Service endpoints populate; `curl` through `port-forward` returns a response |
| `02-broken-selector/` | Service `selector` has a typo (`app: hello-wrong` vs Pod label `app: hello`) — the single highest-ROI label-match bug | Pods run; Service has empty EndpointSlice; `kubectl get endpoints` reveals the bug |
| `03-missing-probe/` | `readinessProbe` removed on a container that takes several seconds to warm up | Pods go Ready immediately before the app can serve; first `curl` through the Service during rollout returns 502/connection reset |

## Suggested learner loop

```bash
# 1. Apply the good one, confirm it works
/kubernetes apply skills/kubernetes/examples/hello-app/01-good
kubectl get pods -n hello-app
kubectl get endpoints -n hello-app
kubectl port-forward -n hello-app svc/hello 8080:80 &
curl -s localhost:8080

# 2. Apply the broken selector, confirm the empty-endpoints symptom
/kubernetes apply skills/kubernetes/examples/hello-app/02-broken-selector
kubectl get endpoints -n hello-app          # ADDRESSES column: <none>
/kubernetes debug "svc/hello has no endpoints after apply"

# 3. Apply the missing probe, confirm the rollout race
/kubernetes apply skills/kubernetes/examples/hello-app/03-missing-probe
kubectl rollout status deployment/hello -n hello-app
# Then port-forward and curl during the next rolling update to see the 502s
```

## Clean up

```bash
kubectl delete namespace hello-app
```

## What this fixture does NOT demonstrate

- **StatefulSets** — these intentionally use `Deployment`; stateful workloads are a separate learning step
- **Ingress** — these use `ClusterIP` + `port-forward`; Ingress is covered in `learn.md`'s section 9
- **RBAC** — the fixtures do not create a dedicated ServiceAccount; the default is fine for a hello-world
- **Secrets** — ConfigMap only; Secret handling has its own learning step
- **Production hardening** — these omit `runAsNonRoot`, `readOnlyRootFilesystem`, and `limits.cpu` so the manifests stay short and the lesson stays focused on the one thing each tier demonstrates

If you expect `k8s-reviewer` to flag items as always-flagged Must Fix (e.g. missing Pod Security Admission label on the `hello-app` namespace), that is intentional — it demonstrates the apply-blocking vs always-flagged split from `rules/k8s-conventions.md`.

## Image choice

All tiers use `kicbase/echo-server:1.0` — a tiny HTTP echo server bundled with minikube's test infrastructure. If `minikube image load kicbase/echo-server:1.0` has not been run, the image is pulled from Docker Hub on first apply. If you prefer a smaller image, swap all three files to `hashicorp/http-echo:1.0.0 -text=hello`.
