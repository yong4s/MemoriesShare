import { defineConfig } from '@hey-api/openapi-ts';

const OPENAPI_INPUT = process.env.OPENAPI_INPUT ?? 'http://localhost:8000/api/schema/?format=json';

export default defineConfig({
  input: OPENAPI_INPUT,
  output: {
    path: 'frontend/js/api/generated',
    format: 'prettier',
  },
  plugins: ['@hey-api/client-axios'],
  useOptions: true,
});
