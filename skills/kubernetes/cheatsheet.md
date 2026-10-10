# kubectl + minikube Cheatsheet

The commands worth memorizing, grouped by task. Loaded on demand by `/kubernetes cheatsheet` — not kept in the always-on skill body.

## Context and config

```bash
kubectl config get-contexts                             # list every cluster you can reach
kubectl config current-context                          # the active one — ALWAYS CHECK before destructive commands
kubectl config use-context <name>                       # switch
kubectl config set-context --current --namespace=<ns>   # pin a default namespace
kubectl config view --minify                            # just the active context
```

## Inspection — the highest-frequency commands

```bash
kubectl get <type>                                      # pods, deployments, svc, cm, secret, ns, nodes, ...
kubectl get <type> -A                                   # all namespaces
kubectl get <type> -o wide                              # extra columns (node, IP)
kubectl get <type> -o yaml                              # full manifest including defaults
kubectl get <type> -l app=hello                         # filter by label
kubectl get <type> --sort-by=.metadata.name
kubectl get <type> -w                                   # watch for changes

kubectl describe <type> <name>                          # events + full detail
kubectl get events --sort-by='.lastTimestamp'           # most recent events first
kubectl explain <type>.<field>                          # schema docs (e.g. kubectl explain pod.spec.containers)
kubectl api-resources                                   # list every resource type + short name
kubectl top nodes / kubectl top pods                    # needs metrics-server addon
```

## Creating resources imperatively (useful for exploration)

```bash
kubectl create deployment hello --image=nginx
kubectl expose deployment hello --port=80 --target-port=80 --type=ClusterIP
kubectl create configmap hello --from-literal=KEY=value --from-file=path/to/file
kubectl create secret generic hello --from-literal=API_KEY=xxx
kubectl create namespace demo
```

Convert imperative to declarative for Git-committable YAML:

```bash
kubectl create deployment hello --image=nginx -o yaml --dry-run=client > deployment.yaml
```

## Applying manifests (the real workflow)

```bash
kubectl apply -f manifest.yaml                         # declarative apply (preferred)
kubectl apply -f manifests/                            # a whole directory
kubectl apply -f manifest.yaml --dry-run=client -o yaml  # validate without applying
kubectl diff -f manifest.yaml                          # what would change
kubectl delete -f manifest.yaml                        # remove everything in the file
```

## Lifecycle: scale, update, rollback

```bash
kubectl scale deployment/hello --replicas=3
kubectl set image deployment/hello app=nginx:1.25
kubectl set env deployment/hello LOG_LEVEL=debug
kubectl set resources deployment/hello --limits=cpu=200m,memory=256Mi
kubectl rollout status deployment/hello
kubectl rollout history deployment/hello
kubectl rollout undo deployment/hello
kubectl rollout restart deployment/hello               # force a new ReplicaSet (useful after ConfigMap change)
```

## Interaction and debugging

```bash
kubectl logs <pod>                                      # stdout/stderr of the main container
kubectl logs <pod> -c <container>                       # multi-container Pod
kubectl logs <pod> --previous                           # the crashed instance's logs
kubectl logs -f -l app=hello                            # follow logs from all Pods matching selector
kubectl logs --tail=100 <pod>

kubectl exec -it <pod> -- /bin/sh                       # shell into the Pod
kubectl exec -it <pod> -c <container> -- /bin/sh
kubectl exec <pod> -- env                               # one-shot command
kubectl exec <pod> -- cat /etc/config/CONFIG_KEY

kubectl port-forward <pod> 8080:80                      # tunnel from your laptop
kubectl port-forward svc/<name> 8080:80                 # or to the Service

kubectl cp <pod>:/path/in/container ./local/file        # copy out
kubectl cp ./local/file <pod>:/path/in/container        # copy in

kubectl run tmp --rm -it --image=busybox --restart=Never -- sh   # one-shot debug Pod
kubectl debug <pod> -it --image=busybox                 # ephemeral debug container
kubectl auth can-i <verb> <resource>                    # check your own permissions
kubectl auth can-i get pods --as=system:serviceaccount:demo:hello   # check someone else's
```

## minikube — lifecycle

```bash
minikube start                                          # with configured defaults
minikube start --driver=docker --cpus=4 --memory=8g
minikube start -p <profile>                             # multiple clusters, isolated
minikube stop
minikube delete
minikube delete --all                                   # wipe every profile
minikube pause / minikube unpause                       # freeze without stopping
```

## minikube — inspection and access

```bash
minikube status
minikube ip                                             # the cluster's IP
minikube logs                                           # control-plane logs
minikube dashboard                                      # browser UI
minikube ssh                                            # shell into the "node"
minikube service <svc>                                  # open the Service in a browser (handles the Docker-driver quirk)
minikube service <svc> --url                            # just print the URL
```

## minikube — networking gotchas (macOS)

```bash
minikube tunnel                                         # required for type: LoadBalancer to get an EXTERNAL-IP
                                                        # runs in foreground, needs sudo on macOS
```

## minikube — images (the local-build workflow)

```bash
# option 1 — build locally, then push into the cluster
docker build -t myapp:dev .
minikube image load myapp:dev

# option 2 — build inside the cluster's Docker daemon
eval $(minikube docker-env)
docker build -t myapp:dev .
# the cluster now sees myapp:dev without a load step
eval $(minikube docker-env -u)                          # unset when done

minikube image ls                                       # what the cluster can see
```

## minikube — addons

```bash
minikube addons list
minikube addons enable ingress                          # NGINX ingress controller
minikube addons enable metrics-server                   # for kubectl top
minikube addons enable dashboard                        # web UI
minikube addons enable registry
minikube addons disable <name>
```

## minikube — multi-node (advanced)

```bash
minikube start --nodes=3                                # three-node cluster for DaemonSet / affinity practice
minikube node add
minikube node list
minikube node delete <name>
```

## Clean up a learning namespace

```bash
kubectl delete namespace demo                           # removes everything in it
kubectl config set-context --current --namespace=default
```

## When all else fails

```bash
kubectl cluster-info                                    # control plane reachable?
minikube status                                         # cluster running?
minikube stop && minikube start                         # the universal reset
minikube delete && minikube start                       # the nuclear reset — wipes everything
```
