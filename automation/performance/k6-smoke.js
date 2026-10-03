import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 3,
  duration: "30s",
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<800"],
  },
};

const baseUrl = __ENV.API_URL || "http://localhost:8000";

function smoke() {
  const login = http.post(
    baseUrl + "/api/v1/auth/login",
    JSON.stringify({
      email: __ENV.DEMO_EMAIL || "admin@medisphere.local",
      password: __ENV.DEMO_PASSWORD || "MediSphere-Demo-2026!",
      organization_slug: "medisphere-health",
    }),
    { headers: { "Content-Type": "application/json" } },
  );
  check(login, { "login succeeds": (response) => response.status === 200 });
  const patients = http.get(baseUrl + "/api/v1/patients");
  check(patients, { "patient search responds": (response) => response.status === 200 });
  sleep(1);
}

export default smoke;
