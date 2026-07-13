import { defineStore } from "pinia";

import { fetchAdminAnalytics, fetchAdminOverview } from "../api/admin";

export const useAdminStore = defineStore("admin", {
  state: () => ({
    overview: null,
    analytics: [],
    loading: false,
  }),
  actions: {
    async loadDashboard() {
      this.loading = true;
      try {
        const [overview, analytics] = await Promise.all([
          fetchAdminOverview(),
          fetchAdminAnalytics(),
        ]);
        this.overview = overview;
        this.analytics = analytics;
      } finally {
        this.loading = false;
      }
    },
  },
});

