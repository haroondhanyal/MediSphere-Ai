variable "kubeconfig_path" {
  type        = string
  description = "Path to kubeconfig for the target cluster."
}
variable "namespace" {
  type    = string
  default = "medisphere"
}
variable "api_image" {
  type        = string
  description = "Immutable API image tag or digest."
}
variable "web_image" {
  type        = string
  description = "Immutable web image tag or digest."
}
variable "api_secret_name" {
  type        = string
  default     = "medisphere-api-secrets"
  description = "Pre-created secret with DATABASE_URL, JWT_SECRET, JWT_ISSUER and CORS_ORIGINS."
}
variable "replicas" {
  type    = number
  default = 2
}
variable "ingress_host" {
  type        = string
  description = "Public DNS name already routed to the cluster ingress."
}
