import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getApiClient } from './client';

// ── tracked items ──────────────────────────────────────────────────────────────

export function useTrackedItems(category?: string) {
  return useQuery({
    queryKey: ['tracked-items', category],
    queryFn: async () => {
      const client = await getApiClient();
      const { data, error } = await client.GET('/v1/wellness/tracked-items/', {
        params: { query: category ? { category } : {} },
      });
      if (error) throw error;
      return data ?? [];
    },
    staleTime: 5 * 60_000,
  });
}

export function useTrackedItem(id: string) {
  return useQuery({
    queryKey: ['tracked-item', id],
    queryFn: async () => {
      const client = await getApiClient();
      const { data, error } = await client.GET('/v1/wellness/tracked-items/{item_id}', {
        params: { path: { item_id: id } },
      });
      if (error) throw error;
      return data;
    },
    enabled: !!id,
    staleTime: 30_000,
  });
}

export function useCreateTrackedItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      category: string;
      name: string;
      metadata: Record<string, unknown>;
      start_date: string;
      end_date?: string | null;
    }) => {
      const client = await getApiClient();
      const { data, error } = await client.POST('/v1/wellness/tracked-items/', {
        body: payload as any,
      });
      if (error) throw error;
      return data!;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tracked-items'] });
    },
  });
}

export function usePatchTrackedItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...patch
    }: {
      id: string;
      name?: string;
      status?: string;
      metadata?: Record<string, unknown>;
    }) => {
      const client = await getApiClient();
      const { data, error } = await client.PATCH('/v1/wellness/tracked-items/{item_id}', {
        params: { path: { item_id: id } },
        body: patch as any,
      });
      if (error) throw error;
      return data!;
    },
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: ['tracked-item', id] });
      qc.invalidateQueries({ queryKey: ['tracked-items'] });
    },
  });
}

export function useDiscontinueTrackedItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const client = await getApiClient();
      const { error } = await client.DELETE('/v1/wellness/tracked-items/{item_id}', {
        params: { path: { item_id: id } },
      });
      if (error) throw error;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tracked-items'] });
    },
  });
}

// ── reminders ──────────────────────────────────────────────────────────────────

export function useUpcomingReminders(hours = 24) {
  return useQuery({
    queryKey: ['upcoming-reminders', hours],
    queryFn: async () => {
      const client = await getApiClient();
      const { data, error } = await client.GET('/v1/wellness/reminders/upcoming', {
        params: { query: { hours } },
      });
      if (error) throw error;
      return data ?? [];
    },
    refetchInterval: 60_000,
  });
}

export function useCreateReminder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      itemId,
      schedule,
      message_template,
    }: {
      itemId: string;
      schedule: Record<string, unknown>;
      message_template: string;
    }) => {
      const client = await getApiClient();
      const { data, error } = await client.POST(
        '/v1/wellness/tracked-items/{item_id}/reminders',
        {
          params: { path: { item_id: itemId } },
          body: { schedule: schedule as any, message_template },
        }
      );
      if (error) throw error;
      return data!;
    },
    onSuccess: (_, { itemId }) => {
      qc.invalidateQueries({ queryKey: ['tracked-item', itemId] });
      qc.invalidateQueries({ queryKey: ['upcoming-reminders'] });
    },
  });
}

// ── log entries ────────────────────────────────────────────────────────────────

export function useLogEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      tracked_item_id: string;
      action: string;
      occurred_at: string;
      fire_key?: string;
    }) => {
      const client = await getApiClient();
      const { data, error } = await client.POST('/v1/wellness/logs/', {
        body: payload as any,
      });
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['upcoming-reminders'] });
      qc.invalidateQueries({ queryKey: ['logs-week'] });
    },
  });
}

export function useWeekLogs() {
  return useQuery({
    queryKey: ['logs-week'],
    queryFn: async () => {
      const from = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();
      const client = await getApiClient();
      const { data, error } = await client.GET('/v1/wellness/logs/', {
        params: { query: { from, limit: 200 } as any },
      });
      if (error) throw error;
      return data ?? [];
    },
    staleTime: 30_000,
  });
}

export function useItemLogs(itemId: string, days = 30) {
  return useQuery({
    queryKey: ['item-logs', itemId, days],
    queryFn: async () => {
      const from = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString();
      const client = await getApiClient();
      const { data, error } = await client.GET('/v1/wellness/logs/', {
        params: {
          query: { tracked_item_id: itemId, from, limit: 200 } as any,
        },
      });
      if (error) throw error;
      return data ?? [];
    },
    enabled: !!itemId,
    staleTime: 60_000,
  });
}

// ── measurements ───────────────────────────────────────────────────────────────

export function useMeasurements(type?: string, from?: string, to?: string) {
  return useQuery({
    queryKey: ['measurements', type, from, to],
    queryFn: async () => {
      const client = await getApiClient();
      const { data, error } = await client.GET('/v1/wellness/measurements/', {
        params: {
          query: {
            ...(type && { type }),
            ...(from && { from }),
            ...(to && { to }),
          } as any,
        },
      });
      if (error) throw error;
      return data ?? [];
    },
  });
}

export function useRecentMeasurements() {
  return useQuery({
    queryKey: ['measurements-recent-30d'],
    queryFn: async () => {
      const from = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();
      const client = await getApiClient();
      const { data, error } = await client.GET('/v1/wellness/measurements/', {
        params: { query: { from, limit: 200 } as any },
      });
      if (error) throw error;
      return data ?? [];
    },
    staleTime: 5 * 60_000,
  });
}

// ── lab reports ────────────────────────────────────────────────────────────────

export function useLabReports() {
  return useQuery({
    queryKey: ['lab-reports'],
    queryFn: async () => {
      const client = await getApiClient();
      const { data, error } = await client.GET('/v1/wellness/lab-reports/', {});
      if (error) throw error;
      return data ?? [];
    },
  });
}

export function useLabReport(id: string) {
  return useQuery({
    queryKey: ['lab-report', id],
    queryFn: async () => {
      const client = await getApiClient();
      const { data, error } = await client.GET('/v1/wellness/lab-reports/{report_id}', {
        params: { path: { report_id: id } },
      });
      if (error) throw error;
      return data!;
    },
    enabled: !!id,
    staleTime: 30_000,
  });
}

export function useDeleteLabReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const client = await getApiClient();
      const { error } = await client.DELETE('/v1/wellness/lab-reports/{report_id}', {
        params: { path: { report_id: id } },
      });
      if (error) throw error;
    },
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: ['lab-reports'] });
      qc.removeQueries({ queryKey: ['lab-report', id] });
    },
  });
}

// ── month logs (30-day adherence) ──────────────────────────────────────────────

export function useMonthLogs() {
  return useQuery({
    queryKey: ['logs-month'],
    queryFn: async () => {
      const from = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();
      const client = await getApiClient();
      const { data, error } = await client.GET('/v1/wellness/logs/', {
        params: { query: { from, limit: 200 } as any },
      });
      if (error) throw error;
      return data ?? [];
    },
    staleTime: 5 * 60_000,
  });
}

// ── all logs (history screen with optional date range) ─────────────────────────

export function useAllLogs(from?: string, to?: string) {
  return useQuery({
    queryKey: ['logs-all', from, to],
    queryFn: async () => {
      const client = await getApiClient();
      const { data, error } = await client.GET('/v1/wellness/logs/', {
        params: {
          query: {
            ...(from && { from }),
            ...(to && { to }),
            limit: 200,
          } as any,
        },
      });
      if (error) throw error;
      return data ?? [];
    },
    staleTime: 2 * 60_000,
  });
}
