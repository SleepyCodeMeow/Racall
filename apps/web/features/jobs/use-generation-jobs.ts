"use client";
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, GenerationJob } from "../../lib/api";

export const isActiveJob = (job: GenerationJob) => job.status === "queued" || job.status === "running";
export function useGenerationJobs(notebook: string, report: (message: string) => void) {
  const query = useQuery({ queryKey: ["jobs", notebook],
    queryFn: () => api<GenerationJob[]>(`/notebooks/${notebook}/jobs`),
    refetchInterval: state => state.state.data?.some(isActiveJob) ? 900 : false,
  });
  useEffect(() => { if (query.error) report(query.error.message); }, [query.error, report]);
  return query;
}
