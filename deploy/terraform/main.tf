resource "kubernetes_namespace_v1" "app" {
  metadata {
    name = var.namespace
  }
}

resource "kubernetes_deployment_v1" "api" {
  metadata {
    name      = "api"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
    labels    = { app = "medisphere-api" }
  }
  spec {
    replicas = var.replicas
    selector {
      match_labels = { app = "medisphere-api" }
    }
    template {
      metadata {
        labels = { app = "medisphere-api" }
      }
      spec {
        container {
          name  = "api"
          image = var.api_image
          port {
            name           = "http"
            container_port = 8000
          }
          env_from {
            secret_ref {
              name = var.api_secret_name
            }
          }
          env {
            name  = "ENVIRONMENT"
            value = "production"
          }
          env {
            name  = "COOKIE_SECURE"
            value = "true"
          }
          env {
            name  = "SEED_DEMO_DATA"
            value = "false"
          }
          env {
            name  = "RUN_MIGRATIONS"
            value = "false"
          }
          readiness_probe {
            http_get {
              path = "/api/v1/health/ready"
              port = "http"
            }
            period_seconds = 10
          }
          liveness_probe {
            http_get {
              path = "/api/v1/health/live"
              port = "http"
            }
            initial_delay_seconds = 20
            period_seconds         = 20
          }
          resources {
            requests = { cpu = "100m", memory = "256Mi" }
            limits   = { cpu = "1", memory = "768Mi" }
          }
        }
      }
    }
  }
}

resource "kubernetes_service_v1" "api" {
  metadata {
    name      = "api"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
    annotations = {
      "prometheus.io/scrape" = "true"
      "prometheus.io/path"   = "/metrics"
      "prometheus.io/port"   = "8000"
    }
  }
  spec {
    selector = { app = "medisphere-api" }
    port {
      name        = "http"
      port        = 8000
      target_port = "http"
    }
  }
}

resource "kubernetes_deployment_v1" "web" {
  metadata {
    name      = "web"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
    labels    = { app = "medisphere-web" }
  }
  spec {
    replicas = var.replicas
    selector {
      match_labels = { app = "medisphere-web" }
    }
    template {
      metadata {
        labels = { app = "medisphere-web" }
      }
      spec {
        container {
          name  = "web"
          image = var.web_image
          port {
            name           = "http"
            container_port = 3000
          }
          env {
            name  = "API_INTERNAL_URL"
            value = "http://api:8000"
          }
          readiness_probe {
            http_get {
              path = "/login"
              port = "http"
            }
            period_seconds = 10
          }
          liveness_probe {
            http_get {
              path = "/login"
              port = "http"
            }
            initial_delay_seconds = 20
            period_seconds         = 20
          }
          resources {
            requests = { cpu = "100m", memory = "256Mi" }
            limits   = { cpu = "1", memory = "768Mi" }
          }
        }
      }
    }
  }
}

resource "kubernetes_service_v1" "web" {
  metadata {
    name      = "web"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }
  spec {
    selector = { app = "medisphere-web" }
    port {
      name        = "http"
      port        = 3000
      target_port = "http"
    }
  }
}

resource "kubernetes_ingress_v1" "web" {
  metadata {
    name      = "web"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
    annotations = {
      "nginx.ingress.kubernetes.io/proxy-read-timeout" = "60"
    }
  }
  spec {
    ingress_class_name = "nginx"
    tls {
      hosts       = [var.ingress_host]
      secret_name = "medisphere-tls"
    }
    rule {
      host = var.ingress_host
      http {
        path {
          path      = "/"
          path_type = "Prefix"
          backend {
            service {
              name = kubernetes_service_v1.web.metadata[0].name
              port {
                number = 3000
              }
            }
          }
        }
      }
    }
  }
}

resource "kubernetes_horizontal_pod_autoscaler_v2" "api" {
  metadata {
    name      = "api"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }
  spec {
    min_replicas = 2
    max_replicas = 6
    scale_target_ref {
      api_version = "apps/v1"
      kind        = "Deployment"
      name        = kubernetes_deployment_v1.api.metadata[0].name
    }
    metric {
      type = "Resource"
      resource {
        name = "cpu"
        target {
          type                = "Utilization"
          average_utilization = 70
        }
      }
    }
  }
}

resource "kubernetes_horizontal_pod_autoscaler_v2" "web" {
  metadata {
    name      = "web"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }
  spec {
    min_replicas = 2
    max_replicas = 6
    scale_target_ref {
      api_version = "apps/v1"
      kind        = "Deployment"
      name        = kubernetes_deployment_v1.web.metadata[0].name
    }
    metric {
      type = "Resource"
      resource {
        name = "cpu"
        target {
          type                = "Utilization"
          average_utilization = 70
        }
      }
    }
  }
}
