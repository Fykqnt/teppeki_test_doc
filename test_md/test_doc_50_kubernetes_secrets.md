# Kubernetes Secrets

## クラスター情報
- クラスター名: prod-k8s-cluster
- API Server: https://k8s-api.company.com:6443

## ServiceAccount Token
- Namespace: production
- ServiceAccount: deploy-sa
- Token: eyJhbGciOiJSUzI1NiIsImtpZCI6IiJ9.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJwcm9kdWN0aW9uIn0...

## Docker Registry Secret
kubectl create secret docker-registry regcred \
  --docker-server=registry.company.com \
  --docker-username=k8s-pull \
  --docker-password=K8s_Pull_P@ss_2024 \
  --docker-email=k8s@company.com

## TLS Secret
- Certificate: production-tls-cert
- Key: production-tls-key
