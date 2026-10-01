"use client";

import { useMutation, useQuery } from "@tanstack/react-query";

import { isInProgress } from "@/lib/review";

import { api, unwrap } from "./client";
import { useInvalidate } from "./invalidate";
import type { ReviewSettingsBody } from "./types";

export const POLL_MS = 3_000;

export const reviewKeys = {
  all: ["reviews"] as const,
  recent: ["reviews", "recent"] as const,
  week: (year: number, week: number) => ["reviews", "week", year, week] as const,
  detail: (id: number) => ["reviews", "detail", id] as const,
  settings: ["settings", "review"] as const,
};

export function useWeekReviews(year: number, week: number) {
  return useQuery({
    queryKey: reviewKeys.week(year, week),
    queryFn: () => unwrap(api.GET("/reviews", { params: { query: { year, week } } })),
    refetchInterval: (query) =>
      query.state.data?.some((review) => isInProgress(review.status)) ? POLL_MS : false,
  });
}

export function useRecentReviews() {
  return useQuery({
    queryKey: reviewKeys.recent,
    queryFn: () => unwrap(api.GET("/reviews")),
  });
}

export function useReview(id: number | null) {
  return useQuery({
    queryKey: reviewKeys.detail(id ?? 0),
    queryFn: () =>
      unwrap(api.GET("/reviews/{review_id}", { params: { path: { review_id: id ?? 0 } } })),
    enabled: id !== null,
    refetchInterval: (query) =>
      query.state.data && isInProgress(query.state.data.status) ? POLL_MS : false,
  });
}

export function useCreateReview() {
  const invalidate = useInvalidate(reviewKeys.all);
  return useMutation({
    mutationFn: (body: { year: number; week: number }) =>
      unwrap(api.POST("/reviews", { body })),
    onSuccess: invalidate,
  });
}

export function useApproveReview() {
  const invalidate = useInvalidate(reviewKeys.all);
  return useMutation({
    mutationFn: (id: number) =>
      unwrap(api.POST("/reviews/{review_id}/approve", { params: { path: { review_id: id } } })),
    onSuccess: invalidate,
  });
}

export function useReviewSettings() {
  return useQuery({
    queryKey: reviewKeys.settings,
    queryFn: () => unwrap(api.GET("/settings/review")),
  });
}

export function useSaveReviewSettings() {
  const invalidate = useInvalidate(reviewKeys.settings);
  return useMutation({
    mutationFn: (body: ReviewSettingsBody) => unwrap(api.PUT("/settings/review", { body })),
    onSuccess: invalidate,
  });
}
