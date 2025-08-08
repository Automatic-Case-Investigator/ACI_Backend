from ai_system_endpoint.automatic_investigation.objects.activity_generation.activity_generator import (
    ActivityGenerator,
)
from ai_system_endpoint.automatic_investigation.objects.query_generation.query_generator import (
    QueryGenerator,
)
from ai_system_endpoint.automatic_investigation.objects.correlator.correlator import Correlator
from soar_endpoint.objects.soar_wrapper.soar_wrapper_builder import SOARWrapperBuilder
from siem_endpoint.objects.siem_wrapper.siem_wrapper_builder import SIEMWrapperBuilder
from soar_endpoint import models as soar_models
from siem_endpoint import models as siem_models
from django.conf import settings
import json


class Investigator:
    def __init__(
        self,
        siem_id,
        soar_id,
        org_id,
        case_id,
        generate_activities=False,
        investigate_siem=False,
    ):
        self.siem_id = siem_id
        self.soar_id = soar_id
        self.org_id = org_id
        self.case_id = case_id
        self.generate_activities = generate_activities
        self.investigate_siem = investigate_siem

    def investigate(self):
        """Investigate the SIEM and SOAR platforms based on the provided parameters."""

        if not self.generate_activities and not self.investigate_siem:
            return {"message": "Success"}

        siem_info_obj = siem_models.SIEMInfo.objects.get(id=self.siem_id)
        siem_wrapper_builder = SIEMWrapperBuilder()
        siem_wrapper = None

        soar_info_obj = soar_models.SOARInfo.objects.get(id=self.soar_id)
        soar_wrapper_builder = SOARWrapperBuilder()
        soar_wrapper = None
        try:
            siem_wrapper = siem_wrapper_builder.build_from_model_object(siem_info_obj=siem_info_obj)
        except TypeError as e:
            return {"error": str(e)}

        try:
            soar_wrapper = soar_wrapper_builder.build_from_model_object(soar_info_obj=soar_info_obj)
        except TypeError as e:
            return {"error": str(e)}

        case_data = None
        case_title = ""
        case_description = ""

        if self.generate_activities or self.investigate_siem:
            case_data = soar_wrapper.get_case(case_id=self.case_id)
            case_title = case_data["title"][: settings.MAXIMUM_STRING_LENGTH]
            case_description = case_data["description"][: settings.MAXIMUM_STRING_LENGTH]
            tasks_data = soar_wrapper.get_tasks(self.org_id, self.case_id)

        if self.generate_activities:
            for task in tasks_data["tasks"]:
                activity_generator = ActivityGenerator()
                activity_generator.set_soarwrapper(soarwrapper=soar_wrapper)
                response = activity_generator.generate_activity(
                    case_title=case_title,
                    case_description=case_description,
                    task_data={
                        "title": task["title"][: settings.MAXIMUM_STRING_LENGTH],
                        "description": task["description"][: settings.MAXIMUM_STRING_LENGTH],
                    },
                )

                for activity in response["activities"]:
                    soar_wrapper.create_task_log(task["id"], activity)

        if self.investigate_siem:
            for task in tasks_data["tasks"]:
                task_log_result = soar_wrapper.get_task_logs(task_id=task["id"])
                for activity in task_log_result["task_logs"]:

                    # Create and run query generator
                    query_generator = QueryGenerator()
                    query_generator.set_soarwrapper(soarwrapper=soar_wrapper)
                    response = query_generator.generate_query(
                        case_title=case_title,
                        case_description=case_description,
                        task_data={
                            "title": task["title"][: settings.MAXIMUM_STRING_LENGTH],
                            "description": task["description"][: settings.MAXIMUM_STRING_LENGTH],
                        },
                        activity=activity["message"],
                    )

                    message_header = "**Automated SIEM Investigation Results:**"
                    final_message = f"{activity['message']}\n\n{message_header}\n\n{response['result']}"

                    # Parse queries from the message
                    query_search_results = siem_wrapper.parse_queries_from_task_log(task_log_str=final_message)

                    # Insert SIEM query results at appropriate positions
                    for result in reversed(query_search_results):
                        query = result["query"]
                        end_pos = result["end_pos"]

                        query_results = siem_wrapper.query(query_str=query)
                        if "results" not in query_results.keys():
                            continue

                        insert_text = f"\n\n*Note: correlation score percentage indicates the confidence of identifying an event as correlated to the investigation*\n\n"
                        insert_text += "| Event ID | Correlation Score (%) | Event Data |\n"
                        insert_text += "|----------|------------|---------------|\n"

                        correlator = Correlator()

                        for event_id in query_results["results"]:
                            event_data = siem_wrapper.get_event(event_id)["result"]
                            event_data_str = json.dumps(event_data)
                            
                            predict_result = correlator.query(
                                event_data=event_data_str,
                                title=case_data["title"],
                                description=case_data["description"],
                                activity=activity["message"],
                                siem_type=siem_info_obj.siem_type
                            )["result"]
                            
                            event_data_str = event_data_str.replace("|", "\\|")
                            event_classification = "Likely correlated" if predict_result > 0.5 else "Likely unrelated"
                            correlation_output_str = f"{int(predict_result * 100)} ({event_classification})"
                            insert_text += f"| `{event_id}` | `{correlation_output_str}` | `{event_data_str}` |\n"

                        final_message = final_message[:end_pos] + insert_text + final_message[end_pos:]

                    # Update the task log with the enriched message
                    soar_wrapper.update_task_log(activity["id"], final_message)

        return {"message": "Success"}
