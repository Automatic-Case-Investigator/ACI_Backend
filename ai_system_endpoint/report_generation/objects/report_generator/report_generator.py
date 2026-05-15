from ai_system_endpoint.report_generation.objects.activity_reporter.activity_reporter import (
    ActivityReporter,
)
from ai_system_endpoint.report_generation.objects.case_reporter.case_reporter import (
    CaseReporter,
)
from ai_system_endpoint.report_generation.objects.task_reporter.task_reporter import (
    TaskReporter,
)
from soar_endpoint.objects.soar_wrapper.soar_wrapper_builder import SOARWrapperBuilder
from soar_endpoint import models as soar_models
from django.conf import settings
import functools
import asyncio


class ReportGenerator:
    def __init__(
        self,
        soar_id: str,
        org_id: str,
        case_id: str,
        report_template: str,
        additional_notes: str | None = None,
    ):
        self.soar_id = soar_id
        self.org_id = org_id
        self.case_id = case_id
        self.report_template = report_template
        self.additional_notes = additional_notes

        soar_info_obj = soar_models.SOARInfo.objects.get(id=self.soar_id)
        soar_wrapper_builder = SOARWrapperBuilder()
        self.soar_wrapper = soar_wrapper_builder.build_from_model_object(
            soar_info_obj=soar_info_obj
        )

        self.activity_reporter = ActivityReporter()
        self.task_reporter = TaskReporter()
        self.case_reporter = CaseReporter()
        self.report_call_semaphore = asyncio.Semaphore(settings.AGENT_MAX_CONCURRENT_CALLS)

    def _truncate(self, value: str) -> str:
        return (value or "")[: settings.MAXIMUM_STRING_LENGTH]

    def _upsert_case_page(self, title: str, content: str, category: str = "report"):
        # Update existing page if title already exists; otherwise create a new one.
        pages_result = self.soar_wrapper.get_pages(
            org_id=self.org_id, case_id=self.case_id
        )
        if "error" in pages_result:
            return pages_result

        for page in pages_result.get("pages", []):
            if page.get("title") == title:
                return self.soar_wrapper.update_page_in_case(
                    case_id=self.case_id,
                    page_id=page["id"],
                    title=title,
                    content=content,
                    category=category,
                    org_id=self.org_id,
                )

        return self.soar_wrapper.create_page_in_case(
            case_id=self.case_id,
            title=title,
            content=content,
            category=category,
            org_id=self.org_id,
        )

    async def _run_limited_report_call(self, call):
        async with self.report_call_semaphore:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, call)

    async def _summarize_activity(
        self, case_title: str, case_description: str, task_data: dict, activity: dict
    ):
        activity_message = activity.get("message", "")

        # response = await self._run_limited_report_call(
        #     functools.partial(
        #         self.activity_reporter.generate_report,
        #         case_title=case_title,
        #         case_description=case_description,
        #         task_title=task_data["title"],
        #         task_description=task_data["description"],
        #         activity=activity_message,
        #         report_template=self.report_template,
        #         additional_notes=self.additional_notes,
        #     ),
        # )

        # if "error" in response:
        #     return response

        # return {
        #     "activity_id": activity.get("id"),
        #     "summary": self._extract_report_text(response),
        # }
        
        return {
            "activity_id": activity.get("id"),
            "summary": activity_message,
        }

    async def _build_task_reports(
        self, case_title: str, case_description: str, tasks: list[dict]
    ):
        loop = asyncio.get_running_loop()

        async def process_task(task):
            task_data = {
                "title": self._truncate(task.get("title", "")),
                "description": self._truncate(task.get("description", "")),
            }

            task_logs_result = await loop.run_in_executor(
                None,
                functools.partial(self.soar_wrapper.get_task_logs, task_id=task["id"]),
            )
            if "error" in task_logs_result:
                return task_logs_result

            activities = task_logs_result.get("task_logs", [])
            if len(activities) == 0:
                task_report = (
                    f"# Task: {task_data['title']}\n\n"
                    f"{task_data['description']}\n\n"
                    f"*No investigation activity was recorded for this task.*"
                )
                task_page_title = f"Task Report - {task_data['title']}"
                task_page_result = await loop.run_in_executor(
                    None,
                    functools.partial(
                        self._upsert_case_page,
                        title=task_page_title,
                        content=task_report,
                    ),
                )
                if "error" in task_page_result:
                    return task_page_result
                return {
                    "task_id": task.get("id"),
                    "task_title": task_data["title"],
                    "task_report": task_report,
                }

            else:
                activity_summary_results = await asyncio.gather(
                    *[
                        self._summarize_activity(
                            case_title=case_title,
                            case_description=case_description,
                            task_data=task_data,
                            activity=activity,
                        )
                        for activity in activities
                    ]
                )

                for result in activity_summary_results:
                    if "error" in result:
                        return result

                activity_reports = []
                for idx, result in enumerate(activity_summary_results):
                    summary_text = result.get("summary") or "No summary available"
                    activity_reports.append(f"### Activity {idx + 1}\n\n{summary_text}")

                activity_report = "\n\n".join(activity_reports)

                activity_page_title = (
                    f"Activity Investigation Report - {task_data['title']}"
                )
                activity_page_result = await loop.run_in_executor(
                    None,
                    functools.partial(
                        self._upsert_case_page,
                        title=activity_page_title,
                        content=activity_report,
                    ),
                )
                if "error" in activity_page_result:
                    return activity_page_result

                task_report_response = await self._run_limited_report_call(
                    functools.partial(
                        self.task_reporter.generate_report,
                        case_title=case_title,
                        case_description=case_description,
                        task_title=task_data["title"],
                        task_description=task_data["description"],
                        activity_reports=activity_reports,
                            additional_notes=self.additional_notes,
                    ),
                )
                if "error" in task_report_response:
                    return task_report_response

                task_report = task_report_response.get("result", "")

                task_page_title = f"Task Report - {task_data['title']}"
                task_page_result = await loop.run_in_executor(
                    None,
                    functools.partial(
                        self._upsert_case_page,
                        title=task_page_title,
                        content=task_report,
                    ),
                )
                if "error" in task_page_result:
                    return task_page_result

                return {
                    "task_id": task.get("id"),
                    "task_title": task_data["title"],
                    "task_report": task_report,
                }

        return await asyncio.gather(*[process_task(task) for task in tasks])

    def generate_report(self):
        case_data = self.soar_wrapper.get_case(case_id=self.case_id)
        if "error" in case_data:
            return case_data

        tasks_data = self.soar_wrapper.get_tasks(
            org_id=self.org_id, case_id=self.case_id
        )
        if "error" in tasks_data:
            return tasks_data

        case_title = self._truncate(case_data.get("title", ""))
        case_description = self._truncate(case_data.get("description", ""))

        task_reports = asyncio.run(
            self._build_task_reports(
                case_title=case_title,
                case_description=case_description,
                tasks=tasks_data.get("tasks", []),
            )
        )

        for result in task_reports:
            if "error" in result:
                return result

        task_report_list = [
            f"# Task Report for Task: {result['task_title']}\n\n{result['task_report']}"
            for result in task_reports
        ]

        case_report_response = asyncio.run(
            self._run_limited_report_call(
                functools.partial(
                    self.case_reporter.generate_report,
                    case_title=case_title,
                    case_description=case_description,
                    task_reports=task_report_list,
                    report_template=self.report_template,
                    additional_notes=self.additional_notes,
                )
            )
        )
        if "error" in case_report_response:
            return case_report_response

        case_report = case_report_response.get("result", "")
        case_page_result = self._upsert_case_page(
            title="Case Report",
            content=case_report,
        )
        if "error" in case_page_result:
            return case_page_result

        return {
            "message": "Success",
            "task_count": len(task_reports),
        }
