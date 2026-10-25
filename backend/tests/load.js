import http from 'k6/http';
import { check } from 'k6';

export const options = {
  scenarios: {
    gateway: { executor: 'shared-iterations', vus: 50, iterations: 1000, exec: 'gateway', maxDuration: '5m' },
    policies: { executor: 'shared-iterations', vus: 50, iterations: 1000, exec: 'policies', maxDuration: '5m' },
  },
  summaryTrendStats: ['avg', 'p(50)', 'p(95)', 'p(99)', 'max'],
  thresholds: { http_req_failed: ['rate<0.01'] },
};

const url = __ENV.AG_URL || 'http://127.0.0.1:8000';
const params = { headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${__ENV.AG_API_KEY}` } };

export function gateway() {
  const response = http.post(`${url}/v1/chat/completions`, JSON.stringify({ model: __ENV.AG_MODEL || 'mock-model', messages: [{ role: 'user', content: 'Benchmark' }], max_tokens: 32 }), params);
  check(response, { 'gateway succeeds': (r) => r.status === 200 });
}

export function policies() {
  const response = http.post(`${url}/v1/tools/authorize`, JSON.stringify({ tool: 'benchmark.lookup', arguments: {} }), params);
  check(response, { 'decision returned': (r) => r.status === 200 && r.json('decision') === 'ALLOW' });
}
