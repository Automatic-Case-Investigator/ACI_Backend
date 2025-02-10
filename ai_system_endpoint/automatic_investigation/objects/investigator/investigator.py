from ai_system_endpoint.automatic_investigation.objects.activity_generation.activity_generator import (
    ActivityGenerator,
)
from soar_endpoint.objects.soar_wrapper.soar_wrapper_builder import SOARWrapperBuilder
from soar_endpoint import models
from django.conf import settings


class Investigator:
    def __init__(
        self,
        soar_id,
        org_id,
        case_id,
        generate_activities=False,
        investigate_siem=False,
    ):
        self.soar_id = soar_id
        self.org_id = org_id
        self.case_id = case_id
        self.generate_activities = generate_activities
        self.investigate_siem = investigate_siem

    def investigate(self):
        if not self.generate_activities and not self.investigate_siem:
            return {"message": "Success"}

        soar_info_obj = models.SOARInfo.objects.get(id=self.soar_id)
        soar_wrapper_builder = SOARWrapperBuilder()
        soar_wrapper = None
        try:
            soar_wrapper = soar_wrapper_builder.build_from_model_object(
                soar_info_obj=soar_info_obj
            )
        except TypeError as e:
            return {"error": str(e)}

        if self.generate_activities:
            case_data = soar_wrapper.get_case(self.case_id)
            case_title = case_data["title"][: settings.MAXIMUM_STRING_LENGTH]
            case_description = case_data["description"][
                : settings.MAXIMUM_STRING_LENGTH
            ]
            tasks_data = soar_wrapper.get_tasks(self.org_id, self.case_id)

            for task in tasks_data["tasks"]:
                activity_generator = ActivityGenerator()
                activity_generator.set_soarwrapper(soarwrapper=soar_wrapper)
                response = activity_generator.generate_activity(
                    case_title=case_title,
                    case_description=case_description,
                    task_data={
                        "title": task["title"][: settings.MAXIMUM_STRING_LENGTH],
                        "description": task["description"][
                            : settings.MAXIMUM_STRING_LENGTH
                        ],
                    },
                )

                for activity in response["activities"]:
                    soar_wrapper.create_task_log(task["id"], activity)

        if self.investigate_siem:
            # TODO: complete the siem investigation control flow
            # read in tasks and get activities of each task
            # generate search list:
            # first iteration: using case title & activity -> search list
            # futher iterations: full log & activity -> search list
            # go over each search result, identify whether we are interested
            # If interested, add the log to the activity log. repeat the process several times
            pass

        return {"message": "Success"}
