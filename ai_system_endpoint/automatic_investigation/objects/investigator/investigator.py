from ACI_Backend.objects.ai_systems.activity_generator.activity_generator import ActivityGenerator
from soar_endpoint.objects.soar_wrapper.soar_wrapper_builder import SOARWrapperBuilder
from soar_endpoint import models


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
            tasks_data = soar_wrapper.get_tasks(self.org_id, self.case_id)
            
            for task in tasks_data["tasks"]:
                activity_generator = ActivityGenerator()
                activity_generator.set_soarwrapper(soarwrapper=soar_wrapper)
                activity_generator.generate_activity(task)

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
