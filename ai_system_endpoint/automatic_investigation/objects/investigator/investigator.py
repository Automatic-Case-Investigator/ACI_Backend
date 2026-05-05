from ai_system_endpoint.automatic_investigation.objects.completion_check.completion_check import (
    ActivityCompletionChecker,
)
from ai_system_endpoint.automatic_investigation.objects.query_generation.query_generator import (
    QueryGenerator,
)
from ai_system_endpoint.automatic_investigation.objects.relevency_filter.relevency_filter import (
    RelevencyFilter,
)
from ai_system_endpoint.automatic_investigation.objects.summarizer.summarizer import (
    ActivitySummarizer,
    QuerySummarizer,
)
from ACI_Backend.objects.siem_schema_retrieval.siem_schema_retrieval_service import (
    get_siem_schema_cache,
)
from soar_endpoint.objects.soar_wrapper.soar_wrapper_builder import SOARWrapperBuilder
from siem_endpoint.objects.siem_wrapper.siem_wrapper_builder import SIEMWrapperBuilder
from soar_endpoint import models as soar_models
from siem_endpoint import models as siem_models
from django.conf import settings
import logging
import json
import re
import asyncio
import functools
import inspect
import hashlib
import datetime


logger = logging.getLogger(__name__)


class Investigator:
    def __init__(
        self,
        siem_id,
        soar_id,
        org_id,
        case_id,
        additional_notes,
        earliest_unit,
        earliest_magnitude,
        vicinity_unit,
        vicinity_magnitude,
        max_iterations,
        max_queries_per_iteration,
    ):
        self.siem_id = siem_id
        self.soar_id = soar_id
        self.org_id = org_id
        self.case_id = case_id
        self.additional_notes = additional_notes

        siem_info_obj = siem_models.SIEMInfo.objects.get(id=self.siem_id)
        siem_wrapper_builder = SIEMWrapperBuilder()

        soar_info_obj = soar_models.SOARInfo.objects.get(id=self.soar_id)
        soar_wrapper_builder = SOARWrapperBuilder()

        self.siem_wrapper = siem_wrapper_builder.build_from_model_object(
            siem_info_obj=siem_info_obj
        )
        self.soar_wrapper = soar_wrapper_builder.build_from_model_object(
            soar_info_obj=soar_info_obj
        )

        self.query_generator = QueryGenerator()
        self.relevency_filter = RelevencyFilter()
        self.completion_checker = ActivityCompletionChecker()
        self.query_summarizer = QuerySummarizer()
        self.activity_summarizer = ActivitySummarizer()

        self.field_top_values_cache: dict[str, list] = {}
        self.field_count_cache: dict[str, int] = {}

        self.relevency_filter.set_soarwrapper(self.soar_wrapper)
        self.query_generator.set_soarwrapper(self.soar_wrapper)
        self.query_generator.set_siem_id(self.siem_id)
        self.completion_checker.set_soarwrapper(self.soar_wrapper)
        self.activity_summarizer.set_soarwrapper(self.soar_wrapper)

        self.explanation_regex = r"(?<=Explanation: )[^\n]*"
        self.final_verdict_regex = r"(?<=Final verdict: )[^\n]*"

        self.earliest_unit = earliest_unit
        self.earliest_magnitude = earliest_magnitude
        self.vicinity_unit = vicinity_unit
        self.vicinity_magnitude = vicinity_magnitude
        self.max_investigation_iter = max_iterations
        self.max_queries_per_iteration = max_queries_per_iteration
        self.max_syntax_fixes = 3
        self.agent_call_semaphore = asyncio.Semaphore(
            settings.AGENT_MAX_CONCURRENT_CALLS
        )

    async def _run_limited_agent_call(self, call):
        async with self.agent_call_semaphore:
            wrapped_callable = getattr(call, "func", call)
            if inspect.iscoroutinefunction(wrapped_callable):
                return await call()

            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, call)
            if inspect.isawaitable(result):
                return await result
            return result

    async def get_relevent_events(
        self,
        case_title: str,
        case_description: str,
        task_data: dict[str, str],
        activity: str,
        query: str,
        query_to_event_ids: dict,
        event_id_to_event_data: dict,
        event_id_to_relevancy_explanation: dict,
        event_id_to_relevancy_verdict: dict,
        web_search: bool = False,
    ) -> list[str]:
        relevent_events = []
        loop = asyncio.get_running_loop()

        # Fetch event data only for events not already cached
        async def fetch_event(event_id):
            event_data = await loop.run_in_executor(
                None, functools.partial(self.siem_wrapper.get_event, event_id)
            )
            return event_id, json.dumps(event_data["result"])

        uncached_event_ids = [
            eid
            for eid in query_to_event_ids[query]
            if eid not in event_id_to_event_data
        ]
        if uncached_event_ids:
            fetch_results = await asyncio.gather(
                *[fetch_event(eid) for eid in uncached_event_ids]
            )
            for event_id, event_data_str in fetch_results:
                event_id_to_event_data[event_id] = event_data_str

        # Create async tasks only for events not yet assessed
        event_relevancy_tasks = [
            (
                event_id,
                self._run_limited_agent_call(
                    functools.partial(
                        self.relevency_filter.check_relevency,
                        case_title=case_title,
                        case_description=case_description,
                        task_data={
                            "title": task_data["title"][
                                : settings.MAXIMUM_STRING_LENGTH
                            ],
                            "description": task_data["description"][
                                : settings.MAXIMUM_STRING_LENGTH
                            ],
                        },
                        activity=activity,
                        additional_notes=self.additional_notes,
                        query=query,
                        event=event_id_to_event_data[event_id],
                    )
                ),
            )
            for event_id in query_to_event_ids[query]
            if event_id not in event_id_to_relevancy_explanation
        ]

        # Execute new relevancy checks in parallel
        if event_relevancy_tasks:
            results = await asyncio.gather(
                *[task for _, task in event_relevancy_tasks], return_exceptions=True
            )

            for (event_id, _), relevency_response in zip(
                event_relevancy_tasks, results
            ):
                if isinstance(relevency_response, Exception):
                    return {"error": str(relevency_response)}

                if "error" in relevency_response.keys():
                    return relevency_response

                relevency_response_text = relevency_response["result"]
                explanation_search = re.search(
                    self.explanation_regex, relevency_response_text
                )
                final_verdict_search = re.search(
                    self.final_verdict_regex, relevency_response_text
                )

                if explanation_search is not None and final_verdict_search is not None:
                    explanation = explanation_search.group(0)
                    final_verdict = final_verdict_search.group(0)
                    is_relevant = final_verdict.strip().upper() == "YES"
                    event_id_to_relevancy_explanation[event_id] = explanation
                    event_id_to_relevancy_verdict[event_id] = is_relevant

        # Collect relevant events using cached verdicts (covers both new and previously seen)
        for event_id in query_to_event_ids[query]:
            if event_id_to_relevancy_verdict.get(event_id):
                relevent_events.append(event_id)

        return relevent_events

    async def summarize_query_results(
        self, query: str, relevent_events: list[str], event_id_to_event_data: dict
    ) -> str:
        relevent_events_str = "\n".join(
            [event_id_to_event_data.get(event_id, "") for event_id in relevent_events]
        )
        response = await self._run_limited_agent_call(
            functools.partial(
                self.query_summarizer.summarize,
                query=query,
                events=relevent_events_str,
                additional_notes=self.additional_notes,
            ),
        )
        logger.debug("Query summarization response received for query=%s", query)
        return response["result"]

    def _extract_summary_and_representative_event(
        self, summary_text: str
    ) -> tuple[str, str]:
        if summary_text is None:
            return "", ""

        summary_match = re.search(
            r"Summary:\s*(.*?)(?:\n+Most representative event id:\s*|$)",
            summary_text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        representative_event_id_match = re.search(
            r"Most representative event id:\s*(.*)$",
            summary_text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        parsed_summary = (
            summary_match.group(1).strip() if summary_match else summary_text.strip()
        )
        representative_event_id = (
            representative_event_id_match.group(1).strip()
            if representative_event_id_match
            else ""
        )
        return parsed_summary, representative_event_id

    async def _process_query(
        self,
        query: str,
        case_title: str,
        case_description: str,
        task_data: dict,
        activity_msg: str,
        prior_seen_event_ids: set[str],
        query_to_event_ids: dict,
        event_id_to_event_data: dict,
        event_id_to_relevancy_explanation: dict,
        event_id_to_relevancy_verdict: dict,
        query_to_seen_stats: dict,
        query_to_summary: dict,
        query_to_representative_event: dict,
        field_map: dict,
    ):
        loop = asyncio.get_running_loop()
        query_results = await loop.run_in_executor(
            None, functools.partial(self.siem_wrapper.query, query_str=query)
        )

        if "results" not in query_results:
            query_to_event_ids[query] = []
            query_to_seen_stats[query] = (0, 0)
            query_to_summary[query] = "Seen-before events (prior iterations): 0/0"
            query_to_representative_event[query] = ""
            return

        query_to_event_ids[query] = query_results["results"]
        total_events = len(query_to_event_ids[query])
        seen_before_count = sum(
            1
            for event_id in query_to_event_ids[query]
            if event_id in prior_seen_event_ids
        )
        query_to_seen_stats[query] = (seen_before_count, total_events)
        logger.debug(
            "Filtering candidate events for query=%s with total_events=%s",
            query,
            total_events,
        )

        relevent_events = await self.get_relevent_events(
            case_title=case_title,
            case_description=case_description,
            task_data=task_data,
            activity=activity_msg,
            query=query,
            query_to_event_ids=query_to_event_ids,
            event_id_to_event_data=event_id_to_event_data,
            event_id_to_relevancy_explanation=event_id_to_relevancy_explanation,
            event_id_to_relevancy_verdict=event_id_to_relevancy_verdict,
        )

        if isinstance(relevent_events, dict) and "error" in relevent_events:
            query_to_summary[query] = (
                f"Seen-before events (prior iterations): {seen_before_count}/{total_events}"
            )
            query_to_representative_event[query] = ""
            return

        logger.debug(
            "Relevant events selected for query=%s count=%s",
            query,
            len(relevent_events),
        )

        summary = await self.summarize_query_results(
            query=query,
            relevent_events=relevent_events,
            event_id_to_event_data=event_id_to_event_data,
        )

        parsed_summary, representative_event_id = (
            self._extract_summary_and_representative_event(summary)
        )

        # Resolve event ID to actual event data.
        if representative_event_id:
            representative_event = event_id_to_event_data.get(
                representative_event_id, representative_event_id
            )
        elif not relevent_events and query_to_event_ids.get(query):
            # If no events passed relevancy but query returned events, use the first event as representative.
            first_event_id = query_to_event_ids[query][0]
            representative_event = event_id_to_event_data.get(
                first_event_id, first_event_id
            )
        else:
            representative_event = ""

        query_to_representative_event[query] = representative_event

        query_to_summary[query] = (
            f"Seen-before events (prior iterations): {seen_before_count}/{total_events}\n\n"
            + f"Summary: {parsed_summary}"
        )
        logger.debug("Built query summary for query=%s", query)

    def _extract_selected_fields(self, selected_fields_result) -> set[str]:
        if selected_fields_result is None:
            return set()

        if isinstance(selected_fields_result, str):
            stripped_value = selected_fields_result.strip()
            if not stripped_value:
                return set()
            try:
                selected_fields_result = json.loads(stripped_value)
            except json.JSONDecodeError:
                return {stripped_value}

        if isinstance(selected_fields_result, list):
            return {str(item).strip() for item in selected_fields_result if str(item).strip()}

        if isinstance(selected_fields_result, dict):
            if "fields" in selected_fields_result:
                return self._extract_selected_fields(selected_fields_result.get("fields"))
            if "selected_fields" in selected_fields_result:
                return self._extract_selected_fields(selected_fields_result.get("selected_fields"))
            if "result" in selected_fields_result:
                return self._extract_selected_fields(selected_fields_result.get("result"))

            return {
                str(key).strip()
                for key, value in selected_fields_result.items()
                if value and str(key).strip()
            }

        return set()

    def _extract_event_fields(self, event_data, prefix: str = "") -> set[str]:
        fields = set()

        if isinstance(event_data, dict):
            for key, value in event_data.items():
                field_name = f"{prefix}.{key}" if prefix else str(key)
                fields.add(field_name)
                fields.update(self._extract_event_fields(value, field_name))
        elif isinstance(event_data, list):
            for item in event_data:
                fields.update(self._extract_event_fields(item, prefix))

        return fields

    async def _update_field_counts_from_events(
        self,
        event_ids: list[str],
        event_id_to_event_data: dict,
        field_map: dict,
    ):
        candidate_fields = set()

        for event_id in event_ids:
            event_data_raw = event_id_to_event_data.get(event_id)
            if not event_data_raw:
                continue

            event_data = event_data_raw
            if isinstance(event_data_raw, str):
                try:
                    event_data = json.loads(event_data_raw)
                except json.JSONDecodeError:
                    continue

            event_payload = event_data.get("_source", event_data)
            candidate_fields.update(self._extract_event_fields(event_payload))

        candidate_fields = {
            field_name for field_name in candidate_fields if field_name in field_map
        }
        if not candidate_fields:
            return

        uncached_fields = [
            field_name
            for field_name in candidate_fields
            if field_name not in self.field_count_cache
        ]

        if uncached_fields:
            loop = asyncio.get_running_loop()
            count_results = await asyncio.gather(
                *[
                    loop.run_in_executor(
                        None,
                        functools.partial(
                            self.siem_wrapper.get_field_count,
                            field=field_name,
                        ),
                    )
                    for field_name in uncached_fields
                ],
                return_exceptions=True,
            )

            for field_name, count_result in zip(uncached_fields, count_results):
                if isinstance(count_result, Exception):
                    continue
                if isinstance(count_result, int):
                    self.field_count_cache[field_name] = count_result

        for field_name in list(candidate_fields):
            count_value = self.field_count_cache.get(field_name)
            if count_value is None:
                continue

            if count_value <= 0:
                field_map.pop(field_name, None)
                continue

            field_info = dict(field_map.get(field_name, {}))
            # field_info["count"] = count_value
            field_map[field_name] = field_info

    async def _investigate_activity(
        self,
        case_title: str,
        case_description: str,
        task_data: dict[str, str],
        activity: dict[str, str],
        searchable_field_map: dict,
    ):
        original_activity = activity["message"]
        if self.additional_notes and self.additional_notes.strip():
            activity["message"] += f"\n\n## Additional Notes\n\n{self.additional_notes}"
        prev_activity_critique = ""
        done_investigation = False
        investigation_iter = 1

        # Local state – each concurrent activity gets its own dicts
        query_to_event_ids: dict[str, list[str]] = {}
        event_id_to_event_data: dict[str, str] = {}
        event_id_to_relevancy_explanation: dict[str, str] = {}
        event_id_to_relevancy_verdict: dict[str, bool] = {}
        seen_event_ids: set[str] = set()
        query_to_seen_stats: dict[str, tuple[int, int]] = {}
        query_to_summary: dict[str, str] = {}
        query_to_representative_event: dict[str, str] = {}

        logger.info("Starting investigation for activity_id=%s", activity.get("id"))

        while (
            not done_investigation and investigation_iter <= self.max_investigation_iter
        ):
            delta_activity_message = (
                "\n\n" + f"## Investigation Iteration {investigation_iter}\n\n"
            )

            task_data_trunc = {
                "title": task_data["title"][: settings.MAXIMUM_STRING_LENGTH],
                "description": task_data["description"][
                    : settings.MAXIMUM_STRING_LENGTH
                ],
            }

            field_map = {k: dict(v) for k, v in searchable_field_map.items()}

            logger.info(
                "Generating queries for activity_id=%s iteration=%s",
                activity.get("id"),
                investigation_iter,
            )
            query_search_results = []
            query_generation_response = ""
            not_query_detected = False
            query_gen_retry_count = 0
            while (
                not query_search_results
                and query_gen_retry_count <= self.max_syntax_fixes
            ):
                response = await self._run_limited_agent_call(
                    functools.partial(
                        self.query_generator.generate_query_from_case,
                        case_title=case_title,
                        case_description=case_description,
                        task_data=task_data_trunc,
                        activity=original_activity,
                        field_map=field_map,
                        prev_activity_critique=prev_activity_critique,
                        additional_notes=self.additional_notes,
                        earliest_unit=self.earliest_unit,
                        earliest_magnitude=self.earliest_magnitude,
                        vicinity_unit=self.vicinity_unit,
                        vicinity_magnitude=self.vicinity_magnitude,
                        max_queries_per_iteration=self.max_queries_per_iteration,
                    ),
                )
                query_generation_response = response["result"]
                
                logger.info("Querying SIEM for activity_id=%s", activity.get("id"))
                query_search_results = self.siem_wrapper.parse_queries_from_task_log(
                    task_log_str=query_generation_response
                )

                syntax_fix_count = 0
                while (
                    not query_search_results
                    and syntax_fix_count < self.max_syntax_fixes
                ):
                    # Attempt to correct query syntax
                    syntax_correction_response = await self._run_limited_agent_call(
                        functools.partial(
                            self.query_generator.fix_queries,
                            input_str=query_generation_response,
                        ),
                    )
                    if "NOT QUERY" in syntax_correction_response["result"]:
                        # Model confirmed no queries exist — document and exit
                        not_query_detected = True
                        break

                    syntax_fix_count += 1
                    query_generation_response = syntax_correction_response["result"]
                    query_search_results = (
                        self.siem_wrapper.parse_queries_from_task_log(
                            task_log_str=query_generation_response
                        )
                    )

                if not_query_detected:
                    break

                query_gen_retry_count += 1

            if not_query_detected or not query_search_results:
                # Either model said no queries exist, or all retries exhausted — document and exit
                delta_activity_message += "\n\n" + query_generation_response
                self.soar_wrapper.update_task_log(
                    activity["id"], activity["message"] + delta_activity_message
                )
                return

            current_queries = [result["query"] for result in query_search_results]
            prior_seen_event_ids = set(seen_event_ids)

            logger.info(
                "Completed SIEM query parsing for activity_id=%s query_count=%s",
                activity.get("id"),
                len(current_queries),
            )

            # Process all queries concurrently
            await asyncio.gather(
                *[
                    self._process_query(
                        query=result["query"],
                        case_title=case_title,
                        case_description=case_description,
                        task_data=task_data_trunc,
                        activity_msg=original_activity,
                        prior_seen_event_ids=prior_seen_event_ids,
                        query_to_event_ids=query_to_event_ids,
                        event_id_to_event_data=event_id_to_event_data,
                        event_id_to_relevancy_explanation=event_id_to_relevancy_explanation,
                        event_id_to_relevancy_verdict=event_id_to_relevancy_verdict,
                        query_to_seen_stats=query_to_seen_stats,
                        query_to_summary=query_to_summary,
                        query_to_representative_event=query_to_representative_event,
                        field_map=field_map,
                    )
                    for result in query_search_results
                ]
            )

            # Update cross-iteration seen-event memory after all queries in this iteration finish.
            for query in current_queries:
                seen_event_ids.update(query_to_event_ids.get(query, []))

            # Group queries by newly found event count so investigation output is easier to scan.
            query_iteration_order = sorted(
                current_queries,
                key=lambda query: (
                    query_to_seen_stats.get(query, (0, 0))[1]
                    - query_to_seen_stats.get(query, (0, 0))[0],
                    query,
                ),
                reverse=True,
            )

            current_new_group = None
            for query in query_iteration_order:
                seen_before_count, total_events = query_to_seen_stats.get(query, (0, 0))
                new_events_count = total_events - seen_before_count
                if new_events_count != current_new_group:
                    current_new_group = new_events_count
                    delta_activity_message += (
                        f"## Queries with {new_events_count} new events found\n\n"
                    )

                delta_activity_message += f"### Query\n`{query}`\n\n"
                delta_activity_message += (
                    f"### Summary\n{query_to_summary.get(query, '')}\n\n"
                )

                if not query_to_event_ids.get(query):
                    delta_activity_message += "---\n\n"
                    continue

                events_md = "| Event ID | Event Data | Analysis |\n"
                events_md += "|----------|------------|------------|\n"

                # Add each event as a table row
                for event_id in query_to_event_ids[query]:
                    event_data_str = event_id_to_event_data.get(event_id, "").replace(
                        "\n", " "
                    )  # Replace newlines with spaces
                    relevancy_explanation = event_id_to_relevancy_explanation.get(
                        event_id, ""
                    ).replace("\n", " ")
                    events_md += (
                        f"| {event_id} | {event_data_str} | {relevancy_explanation} |\n"
                    )

                events_md += "\n"  # Extra newline after table for spacing

                query_result_id = hashlib.sha256(
                    f"{query}:{datetime.datetime.now().timestamp()}".encode()
                ).hexdigest()[:16]
                self.soar_wrapper.create_page_in_case(
                    case_id=self.case_id,
                    title=query_result_id,
                    content=events_md,
                    category="ACI_Evidence",
                    org_id=self.org_id,
                )
                delta_activity_message += (
                    f"**Evidence in document {query_result_id}**\n\n---\n\n"
                )

            # Invoke completion check to see if the activity is fulfilled
            logger.info(
                "Analyzing activity completeness for activity_id=%s iteration=%s",
                activity.get("id"),
                investigation_iter,
            )
            completion_analysis = await self._run_limited_agent_call(
                functools.partial(
                    self.completion_checker.check_completeness,
                    case_title=case_title,
                    case_description=case_description,
                    task_data=task_data_trunc,
                    activity=f"{original_activity}\n\n{prev_activity_critique}",
                    additional_notes=self.additional_notes,
                    queries=current_queries,
                    query_summaries=[
                        query_to_summary.get(query, "") for query in current_queries
                    ],
                ),
            )

            logger.debug(
                "Completion analysis response received for activity_id=%s",
                activity.get("id"),
            )

            result_text = completion_analysis["result"]

            explanation = ""
            final_verdict = ""

            exp_index = result_text.find("Explanation:")
            verdict_index = result_text.find("Final verdict:")

            if exp_index == -1 or verdict_index == -1:
                done_investigation = True
            else:
                # Everything up to final verdict
                explanation = result_text[
                    exp_index + len("Explanation:") : verdict_index
                ].strip()

                prev_activity_critique += (
                    f"\n\n## Investigation Iteration {investigation_iter}\n"
                )
                prev_activity_critique += "### Query Results Summary\n"
                current_new_group = None
                for query in query_iteration_order:
                    seen_before_count, total_events = query_to_seen_stats.get(
                        query, (0, 0)
                    )
                    new_events_count = total_events - seen_before_count
                    if new_events_count != current_new_group:
                        current_new_group = new_events_count
                        prev_activity_critique += (
                            f"- New events found: {new_events_count}\n"
                        )

                    query_summary = " ".join(query_to_summary.get(query, "").split())
                    prev_activity_critique += f"- Query: {query}\n"
                    prev_activity_critique += f"  Summary: {query_summary}\n"

                    representative_event = " ".join(
                        query_to_representative_event.get(query, "").split()
                    )
                    if representative_event:
                        prev_activity_critique += (
                            f"  Most Representative Event: {representative_event}\n"
                        )

                prev_activity_critique += "\n### Critique\n"
                prev_activity_critique += explanation

                # Everything after final verdict up to the next new line
                final_verdict = (
                    result_text[verdict_index + len("Final verdict:") :]
                    .split("\n")[0]
                    .strip()
                )

                logger.info(
                    "Completion verdict for activity_id=%s iteration=%s verdict=%s",
                    activity.get("id"),
                    investigation_iter,
                    final_verdict,
                )

                if final_verdict.upper() == "YES":
                    # Write activity summary
                    done_investigation = True
                else:
                    # Document the reason for incompleteness in the activity log and continue the loop
                    delta_activity_message += (
                        f"\n\n### Iteration Analysis\n{explanation}\n\n"
                    )

            logger.info(
                "Writing investigation iteration to SOAR for activity_id=%s iteration=%s",
                activity.get("id"),
                investigation_iter,
            )

            # Update the activity log once per iteration.
            activity["message"] += delta_activity_message

            # Either the investigation is complete or no more iteration is ahead
            should_summarize = (
                done_investigation or investigation_iter >= self.max_investigation_iter
            )
            if should_summarize:
                summary_response = await self._run_limited_agent_call(
                    functools.partial(
                        self.activity_summarizer.summarize,
                        case_title=case_title,
                        case_description=case_description,
                        task_data=task_data_trunc,
                        activity=activity["message"],
                        additional_notes=self.additional_notes,
                        queries=current_queries,
                        query_summaries=[
                            query_to_summary.get(query, "") for query in current_queries
                        ],
                    ),
                )
                summary_text = summary_response["result"]

                if done_investigation:
                    activity[
                        "message"
                    ] += f"\n\n## Final Activity Summary\n\n{summary_text}"

            self.soar_wrapper.update_task_log(activity["id"], activity["message"])

            investigation_iter += 1

    def investigate(self):
        """Investigate the SIEM and SOAR platforms based on the provided parameters."""
        case_data = self.soar_wrapper.get_case(case_id=self.case_id)
        case_title = case_data["title"][: settings.MAXIMUM_STRING_LENGTH]
        case_description = case_data["description"][: settings.MAXIMUM_STRING_LENGTH]
        tasks_data = self.soar_wrapper.get_tasks(self.org_id, self.case_id)

        searchable_field_map, field_counts = get_siem_schema_cache(
            siem_wrapper=self.siem_wrapper,
            siem_id=self.siem_id,
        )
        if field_counts:
            self.field_count_cache.update(field_counts)

        # Run async investigation tasks
        async def run_investigations():
            loop = asyncio.get_running_loop()

            # Fetch all task logs concurrently
            async def fetch_task_logs(task):
                return task, await loop.run_in_executor(
                    None,
                    functools.partial(
                        self.soar_wrapper.get_task_logs, task_id=task["id"]
                    ),
                )

            task_and_logs = await asyncio.gather(
                *[fetch_task_logs(task) for task in tasks_data["tasks"]]
            )

            investigation_tasks = []
            for task, task_log_result in task_and_logs:
                for activity in task_log_result["task_logs"]:
                    task_coro = self._investigate_activity(
                        case_title=case_title,
                        case_description=case_description,
                        task_data={
                            "title": task["title"][: settings.MAXIMUM_STRING_LENGTH],
                            "description": task["description"][
                                : settings.MAXIMUM_STRING_LENGTH
                            ],
                        },
                        activity=activity,
                        searchable_field_map=searchable_field_map,
                    )
                    investigation_tasks.append(task_coro)

            # Run all investigations concurrently
            await asyncio.gather(*investigation_tasks)

        asyncio.run(run_investigations())

        return {"message": "Success"}

    def investigate_single_activity(self, activity_id):
        """Investigate a single activity based on the provided activity ID."""
        case_data = self.soar_wrapper.get_case(case_id=self.case_id)
        case_title = case_data["title"][: settings.MAXIMUM_STRING_LENGTH]
        case_description = case_data["description"][: settings.MAXIMUM_STRING_LENGTH]
        tasks_data = self.soar_wrapper.get_tasks(self.org_id, self.case_id)

        searchable_field_map, field_counts = get_siem_schema_cache(
            siem_wrapper=self.siem_wrapper,
            siem_id=self.siem_id,
        )
        if field_counts:
            self.field_count_cache.update(field_counts)

        logger.info("Investigating single activity_id=%s", activity_id)

        for task in tasks_data["tasks"]:
            task_log_result = self.soar_wrapper.get_task_logs(task_id=task["id"])
            for activity in task_log_result["task_logs"]:
                if activity["id"] == activity_id:
                    # Found the activity, investigate it
                    asyncio.run(
                        self._investigate_activity(
                            case_title=case_title,
                            case_description=case_description,
                            task_data={
                                "title": task["title"][
                                    : settings.MAXIMUM_STRING_LENGTH
                                ],
                                "description": task["description"][
                                    : settings.MAXIMUM_STRING_LENGTH
                                ],
                            },
                            activity=activity,
                            searchable_field_map=searchable_field_map,
                        )
                    )
                    return {"message": "Success"}

        return {"error": "Activity not found"}
