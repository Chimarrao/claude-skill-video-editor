import {defineConfig} from 'vite';
import motionCanvas from '@motion-canvas/vite-plugin';

// Prévia dos MODELOS DE LISTA (porta 9000): npx vite --config vite.models.config.ts --port 9000
export default defineConfig({
  plugins: [motionCanvas({project: './src/project_models.ts'})],
});
