from datetime import datetime, timezone, timedelta
from ACI_Backend.objects.job_scheduler.job_scheduler import job_scheduler
from soar_endpoint.objects.soar_wrapper.soar_wrapper_builder import SOARWrapperBuilder
from soar_endpoint import models as soar_models
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication


class DashboardSummaryView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        soar_id = request.GET.get("soar_id")
        org_id  = request.GET.get("org_id")

        # ── job stats from Redis ───────────────────────────────────────────────
        all_jobs  = job_scheduler.get_jobs().get("jobs", [])
        total     = len(all_jobs)
        completed = sum(1 for j in all_jobs if j.get("status") == "completed")
        failed    = sum(1 for j in all_jobs if j.get("status") == "failed")
        pending   = sum(1 for j in all_jobs if j.get("status") in ("queued", "running"))
        success_rate = round(completed / total * 100) if total > 0 else 0

        # 14-day histogram
        today = datetime.now(timezone.utc).date()
        day_counts = {(today - timedelta(days=i)): 0 for i in range(13, -1, -1)}
        for j in all_jobs:
            try:
                d = datetime.fromtimestamp(float(j["createdAt"]), tz=timezone.utc).date()
                if d in day_counts:
                    day_counts[d] += 1
            except (KeyError, ValueError, TypeError):
                pass
        by_day = [{"date": str(d), "count": c} for d, c in day_counts.items()]

        def safe_ts(j):
            try:
                return float(j.get("createdAt", 0))
            except (ValueError, TypeError):
                return 0.0

        recent_jobs = sorted(all_jobs, key=safe_ts, reverse=True)[:5]

        # ── SOAR data (optional, degrades gracefully) ─────────────────────────
        orgs_count   = 0
        recent_cases = []

        if soar_id is not None:
            try:
                soar_info    = soar_models.SOARInfo.objects.get(id=soar_id)
                soar_wrapper = SOARWrapperBuilder().build_from_model_object(soar_info)

                org_data = soar_wrapper.get_organizations()
                if "organizations" in org_data:
                    orgs_count = len(org_data["organizations"])

                if org_id is not None:
                    cases_data = soar_wrapper.get_cases(
                        org_id=org_id,
                        search_str=None,
                        page_size=5,
                        time_sort_type=0,  # desc by createdAt
                        page_number=1,
                    )
                    for c in cases_data.get("cases", []):
                        recent_cases.append({
                            "id":    c.get("id"),
                            "title": c.get("title"),
                            "tlp":   c.get("tlp"),
                            "pap":   c.get("pap"),
                        })
            except Exception:
                pass  # SOAR offline — return zeroed fields

        return Response({
            "job_stats": {
                "total":        total,
                "completed":    completed,
                "failed":       failed,
                "pending":      pending,
                "success_rate": success_rate,
                "by_day":       by_day,
            },
            "recent_jobs":  recent_jobs,
            "orgs_count":   orgs_count,
            "recent_cases": recent_cases,
        }, status=status.HTTP_200_OK)
