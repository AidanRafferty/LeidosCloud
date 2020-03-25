from django.apps import AppConfig

from .utils_delete import delete_host


class LeidosCloudAppConfig(AppConfig):
    # Standard Django contents of the appconfig
    name = "leidoscloud"
    verbose_name = "Leidos Cloud"

    # Our custom method to run the death playbook on Django startup
    def ready(self):
        # Run the population script if it does not already exist
        # Check for an expected entry
        API = self.get_model("API")

        try:
            if API.objects.filter(name="none").count() == 0:
                from .populate_db import populate

                print("Database empty: running population script")
                populate()
        except:
            print("Failed to populate database. You likely haven't migrated yet.")

        # Only attempt to update transition if transition table exists
        from django.db import connection

        # Hardcoded hack but gets the job done for now
        if "leidoscloud_transition" in connection.introspection.table_names():

            # Import here so the application can still start
            transition = self.get_model("Transition")
            from django.utils import timezone
            from .utils_host import get_current_cloud_host

            try:
                latest_transition = transition.objects.latest("start_time")
                current_host = get_current_cloud_host()
                # First time starting on new host actions:
                if latest_transition.end_provider == current_host:
                    if latest_transition.end_time is None:
                        latest_transition.succeeded = True
                        latest_transition.end_time = timezone.now()
                        latest_transition.save()
                        # The transition succeeded! Let's delete the previous instance
                        delete_host(latest_transition.start_provider)

            except transition.DoesNotExist:
                print("Could not find a previous transition to update the end_time on!")
            except Exception as e:
                print("failed to update transition: probably: db not ready yet")
                print(e)
