import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          // Keep the chart runtime cached, but split its independently loaded
          // subsystems so no single lazy chunk dominates first navigation.
          if (id.includes('/zrender/')) return 'chart-renderer'
          if (id.includes('/echarts/lib/chart/')) return 'chart-series'
          if (id.includes('/echarts/lib/component/')) return 'chart-components'
          if (id.includes('/echarts/lib/')) return 'chart-core'
          return undefined
        },
      },
      input: {
        main: 'index.html',
        overview: 'overview/index.html',
        scenarioData: 'scenario-data/index.html',
        standardCheck: 'standard-check/index.html',
        dataSelection: 'data-selection/index.html',
        identificationModeling: 'identification-modeling/index.html',
        closedLoopOptimization: 'closed-loop-optimization/index.html',
        agentReview: 'agent-review/index.html',
        reportExport: 'report-export/index.html',
        pipelineBuilder: 'pipeline-builder/index.html',
        experiments: 'experiments/index.html',
      },
    },
  },
})
