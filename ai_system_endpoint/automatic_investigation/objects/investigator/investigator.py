from ai_system_endpoint.automatic_investigation.objects.completion_check.completion_check import ActivityCompletionChecker
from ai_system_endpoint.automatic_investigation.objects.query_generation.query_generator import (
    QueryGenerator,
)
from ai_system_endpoint.automatic_investigation.objects.relevency_filter.relevency_filter import RelevencyFilter
from ai_system_endpoint.automatic_investigation.objects.summarizer.summarizer import ActivitySummarizer, QuerySummarizer
from soar_endpoint.objects.soar_wrapper import soar_wrapper
from soar_endpoint.objects.soar_wrapper.soar_wrapper_builder import SOARWrapperBuilder
from siem_endpoint.objects.siem_wrapper.siem_wrapper_builder import SIEMWrapperBuilder
from soar_endpoint import models as soar_models
from siem_endpoint import models as siem_models
from django.conf import settings
import json
import re
import asyncio
import hashlib
import datetime

class Investigator:
    def __init__(
        self,
        siem_id,
        soar_id,
        org_id,
        case_id,
    ):
        self.siem_id = siem_id
        self.soar_id = soar_id
        self.org_id = org_id
        self.case_id = case_id
        
        siem_info_obj = siem_models.SIEMInfo.objects.get(id=self.siem_id)
        siem_wrapper_builder = SIEMWrapperBuilder()

        soar_info_obj = soar_models.SOARInfo.objects.get(id=self.soar_id)
        soar_wrapper_builder = SOARWrapperBuilder()
        
        self.siem_wrapper = siem_wrapper_builder.build_from_model_object(siem_info_obj=siem_info_obj)
        self.soar_wrapper = soar_wrapper_builder.build_from_model_object(soar_info_obj=soar_info_obj)
        
        self.query_generator = QueryGenerator()
        self.relevency_filter = RelevencyFilter()
        self.completion_checker = ActivityCompletionChecker()
        self.query_summarizer = QuerySummarizer()
        self.activity_summarizer = ActivitySummarizer()
        
        self.relevency_filter.set_soarwrapper(self.soar_wrapper)
        self.query_generator.set_soarwrapper(self.soar_wrapper)
        self.completion_checker.set_soarwrapper(self.soar_wrapper)
        self.activity_summarizer.set_soarwrapper(self.soar_wrapper)
        
        self.query_to_event_ids: dict[str, list[str]] = dict()
        self.event_id_to_event_data: dict[str, str] = dict()
        self.query_to_summary: dict[str, str] = dict()
        self.explanation_regex = r"(?<=Explanation: )[^\n]*"
        self.final_verdict_regex = r"(?<=Final verdict: )[^\n]*"
        self.max_investigation_iter = 5
        self.max_syntax_fixes = 3
        
    async def get_relevent_events(self, case_title: str, case_description: str, task_data: dict[str, str], activity: str, query: str, web_search: bool = False) -> list[str]:
        relevent_events = []
        
        # Prepare all event data first
        event_relevancy_tasks = []
        for event_id in self.query_to_event_ids[query]:
            event_data = self.siem_wrapper.get_event(event_id)["result"]
            event_data_str = json.dumps(event_data)
            self.event_id_to_event_data[event_id] = event_data_str
            
            # Create async task for relevancy check
            task = self.relevency_filter.check_relevency(
                case_title=case_title,
                case_description=case_description,
                task_data={
                    "title": task_data["title"][: settings.MAXIMUM_STRING_LENGTH],
                    "description": task_data["description"][: settings.MAXIMUM_STRING_LENGTH],
                },
                activity=activity,
                query=query,
                event=event_data_str,
            )
            event_relevancy_tasks.append((event_id, task))
        
        # Execute all relevancy checks in parallel
        results = await asyncio.gather(*[task for _, task in event_relevancy_tasks], return_exceptions=True)
        
        # Process results
        for (event_id, _), relevency_response in zip(event_relevancy_tasks, results):
            if isinstance(relevency_response, Exception):
                return {"error": str(relevency_response)}
            
            if "error" in relevency_response.keys():
                return relevency_response
            
            relevency_response_text = relevency_response["result"]
            explanation_search = re.search(self.explanation_regex, relevency_response_text)
            final_verdict_search = re.search(self.final_verdict_regex, relevency_response_text)
            
            if explanation_search is not None and final_verdict_search is not None:
                explanation = explanation_search.group(0)
                final_verdict = final_verdict_search.group(0)
                if final_verdict_search is not None and final_verdict.strip().upper() == "YES":
                    relevent_events.append(event_id)
                
        return relevent_events
    
    def summarize_query_results(self, query: str, relevent_events: list[str]) -> str:
        relevent_events_str = "\n".join([self.event_id_to_event_data[event_id] for event_id in relevent_events])
        response = self.query_summarizer.summarize(query=query, events=relevent_events_str)
        print(response)
        return response["result"]
    
    async def investigate_activity(self, case_title: str, case_description: str, task_data: dict[str, str], activity: dict[str, str]):
        original_activity = activity["message"]
        current_activity_summary = ""
        prev_activity_critique = ""
        done_investigation = False
        investigation_iter = 1
        
        print("Start Investigating Activity")
        
        while not done_investigation and investigation_iter <= self.max_investigation_iter:
            delta_activity_message = "\n\n" + f"## Investigation Iteration {investigation_iter}\n\n"
            
            field_map = self.siem_wrapper.get_available_fields()      
            
            print("Generating Queries")
            response = self.query_generator.generate_query_from_case(
                case_title=case_title,
                case_description=case_description,
                task_data={
                    "title": task_data["title"][: settings.MAXIMUM_STRING_LENGTH],
                    "description": task_data["description"][: settings.MAXIMUM_STRING_LENGTH],
                },
                activity=activity["message"] if len(current_activity_summary) == 0 else current_activity_summary,
                field_map=field_map,
                prev_activity_critique=prev_activity_critique,
            )
            
            query_generation_response = response["result"]
            query_search_results = self.siem_wrapper.parse_queries_from_task_log(task_log_str=query_generation_response)
            
            syntax_fix_count = 0
            while not query_search_results and syntax_fix_count < self.max_syntax_fixes:
                # Attempt to correct query syntax
                syntax_correction_response = self.query_generator.fix_queries(input_str=query_generation_response)
                if "NOT QUERY" in syntax_correction_response["result"]:
                    # No queries were generated, document the reason and exit the investigation loop
                    delta_activity_message += "\n\n" + query_generation_response
                    self.soar_wrapper.update_task_log(activity["id"], activity["message"] + delta_activity_message)
                    return
                
                syntax_fix_count += 1
                query_generation_response = syntax_correction_response["result"]
                query_search_results = self.siem_wrapper.parse_queries_from_task_log(task_log_str=query_generation_response)
                
                

            # Parse queries from the message
            current_queries = []

            # Insert SIEM query results at appropriate positions
            for result in query_search_results:
                query = result["query"]
                current_queries.append(query)

                # Query event data from SIEM
                query_results = self.siem_wrapper.query(query_str=query)
                if "results" not in query_results.keys():
                    continue
                
                self.query_to_event_ids[query] = query_results["results"]
                
                print("Filtering for events: ", query_results["results"])
                
                # Filter out semanticly unrelated events
                relevent_events = await self.get_relevent_events(
                    case_title=case_title,
                    case_description=case_description,
                    task_data={
                        "title": task_data["title"][: settings.MAXIMUM_STRING_LENGTH],
                        "description": task_data["description"][: settings.MAXIMUM_STRING_LENGTH],
                    },
                    activity=activity["message"] if len(current_activity_summary) == 0 else current_activity_summary,
                    query=query,
                )
                
                print("Relevent Events: ", relevent_events)
                
                # Summarize query results based on semanticly relevent events
                query_summary = self.summarize_query_results(query=query, relevent_events=relevent_events)
                self.query_to_summary[query] = query_summary
                
                print(f"Summary for query {query}: {query_summary}")

            for query in current_queries:
                delta_activity_message += f"### Query\n`{query}`\n\n"
                delta_activity_message += f"### Summary\n{self.query_to_summary[query]}\n\n"
                
                if not self.query_to_event_ids[query]:
                    delta_activity_message += "---\n\n"
                    continue
                
                events_md = "| Event ID | Event Data |\n"
                events_md += "|----------|------------|\n"
                
                # Add each event as a table row
                for event_id in self.query_to_event_ids[query]:
                    event_data_str = self.event_id_to_event_data[event_id].replace("\n", " ")  # Replace newlines with spaces
                    events_md += f"| {event_id} | {event_data_str} |\n"
                
                events_md += "\n"  # Extra newline after table for spacing
                
                query_result_id = hashlib.sha256(f"{query}:{datetime.datetime.now().timestamp()}".encode()).hexdigest()[:16]
                self.soar_wrapper.create_page_in_case(
                    case_id=self.case_id,
                    title=query_result_id,
                    content=events_md,
                    category="ACI_Evidence"
                )
                delta_activity_message += f"**Evidence in document {query_result_id}**\n\n---\n\n"
                
            
            # Invoke completion check to see if the activity is fulfilled
            print("Analyzing activity completeness")
            completion_analysis = self.completion_checker.check_completeness(
                case_title=case_title,
                case_description=case_description,
                task_data={
                    "title": task_data["title"][:settings.MAXIMUM_STRING_LENGTH],
                    "description": task_data["description"][:settings.MAXIMUM_STRING_LENGTH],
                },
                activity=activity["message"] if len(current_activity_summary) == 0 else current_activity_summary,
                queries=current_queries,
                query_summaries=[self.query_to_summary[query] for query in current_queries],
            )

            print(completion_analysis)

            result_text = completion_analysis["result"]

            explanation = ""
            final_verdict = ""

            exp_index = result_text.find("Explanation:")
            verdict_index = result_text.find("Final verdict:")

            if exp_index == -1 or verdict_index == -1:
                done_investigation = True
            else:
                # Everything up to final verdict
                explanation = result_text[exp_index + len("Explanation:"):verdict_index].strip()
                prev_activity_critique += f"\n\n**Investigation Iteration {investigation_iter}**"
                prev_activity_critique += "\n\nQueries:\n"
                for query in current_queries:
                    prev_activity_critique += f"- {query}\n"
                    
                prev_activity_critique += "\n\n" + explanation
                
                # Everything after final verdict up to the next new line
                final_verdict = result_text[verdict_index + len("Final verdict:"):].split("\n")[0].strip()

                print(explanation, final_verdict)

                if final_verdict.upper() == "YES":
                    # Write activity summary
                    done_investigation = True
                else:
                    # Document the reason for incompleteness in the activity log and continue the loop
                    delta_activity_message += f"\n\n### Iteration Analysis\n{explanation}\n\n"
                
            print("Writing to SOAR")
            
            # Update the activity to the SOAR platform
            activity["message"] += delta_activity_message
            self.soar_wrapper.update_task_log(activity["id"], activity["message"])
            
            if done_investigation or investigation_iter < self.max_investigation_iter:
                # If more iterations are ahead, summarize the investigation result into a single paragraph to save context
                current_activity_summary = self.activity_summarizer.summarize(
                    case_title=case_title,
                    case_description=case_description,
                    task_data={
                        "title": task_data["title"][: settings.MAXIMUM_STRING_LENGTH],
                        "description": task_data["description"][: settings.MAXIMUM_STRING_LENGTH],
                    },
                    activity=activity["message"],
                    queries=current_queries,
                    query_summaries=[self.query_to_summary[query] for query in current_queries],
                )
                current_activity_summary = original_activity + "\n\n" + current_activity_summary["result"]
                    
            investigation_iter += 1
    
    def investigate(self):
        """Investigate the SIEM and SOAR platforms based on the provided parameters."""
        case_data = self.soar_wrapper.get_case(case_id=self.case_id)
        case_title = case_data["title"][: settings.MAXIMUM_STRING_LENGTH]
        case_description = case_data["description"][: settings.MAXIMUM_STRING_LENGTH]
        tasks_data = self.soar_wrapper.get_tasks(self.org_id, self.case_id)

        # Run async investigation tasks
        async def run_investigations():
            for task in tasks_data["tasks"]:
                task_log_result = self.soar_wrapper.get_task_logs(task_id=task["id"])
                for activity in task_log_result["task_logs"]:
                    await self.investigate_activity(
                        case_title=case_title,
                        case_description=case_description,
                        task_data={
                            "title": task["title"][: settings.MAXIMUM_STRING_LENGTH],
                            "description": task["description"][: settings.MAXIMUM_STRING_LENGTH],
                        },
                        activity=activity,
                    )
        
        asyncio.run(run_investigations())
                    
        return {"message": "Success"}
