output "namespace" {
  value = kubernetes_namespace_v1.app.metadata[0].name
}
output "web_service" {
  value = kubernetes_service_v1.web.metadata[0].name
}
output "api_service" {
  value = kubernetes_service_v1.api.metadata[0].name
}
