import os
import random
import string
from datetime import datetime
from pathlib import Path

from django.contrib.auth.models import User
from django.template import Context, Template
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from leidoscloud.models import *

from . import utils_stock_api
from leidoscloud.utils_stock_api import save_stock_data, save_best_prediction
from .populate_db import populate
from .utils_host import DELETE_LOG_TXT, MAIN_LOG_TXT
from .utils_playbook import (
    move_self,
    CloudSurfAlreadyInProgressException,
)


# Create your tests here.


class TestRunnerTestTestCase(TestCase):
    def test_unit_tests_are_understood_and_can_pass(self):
        """Unit tests run and are able to pass"""
        populate()
        test_value = 5
        self.assertEqual(test_value, 5)


class TestIndexPage(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        user = User.objects.create(username="newtestuser")
        user.set_password("12345")
        user.save()
        self.client.login(username="newtestuser", password="12345")
        populate()

    @classmethod
    def tearDownClass(cls):
        User.objects.filter(username="newtestuser").delete()
        super().tearDownClass()

    def test_index_page_renders(self):
        response = self.client.get(reverse("index"), follow=True)
        self.assertContains(response, "Transitions")

    def test_current_host_is_detected_properly(self):
        # On the test runner and locally, the host should be reported as "Unknown Host"
        response = self.client.get(reverse("index"))
        bv_file = Path("/sys/devices/virtual/dmi/id/sys_vendor")
        if bv_file.exists():
            self.assertNotIn("Unknown", response)
        else:
            self.assertContains(response, "Unknown Host")

    def test_running_time_renders_with_end_prov_correctly(self):
        """Create DB entry with end time, check if index page displays 0 minutes"""
        user = User.objects.create_user("Miles")
        start = API.objects.get_or_create(name="google", is_provider=True)[0]
        start.save()
        end = API.objects.get_or_create(name="azure", is_provider=True)[0]
        end.save()
        t = Transition.objects.get_or_create(user=user)[0]
        t.start_provider = start
        t.end_provider = end
        time_now = timezone.now()
        t.end_time = time_now
        t.save()
        response = self.client.get(reverse("index"))
        self.assertContains(response, "0\xa0minutes")

    def test_running_time_renders_with_no_transition(self):

        response = self.client.get(reverse("index"))
        self.assertContains(response, "eternity and/or never")

    def test_running_time_renders_with_no_end_time(self):
        populate()
        user = User.objects.create_user("James")
        azure = API.objects.get(name="azure")
        google_cloud = API.objects.get(name="google")
        t = Transition.objects.get_or_create(
            user=user,
            start_time=timezone.now(),
            end_time=None,
            start_provider=azure,
            end_provider=google_cloud,
        )[0]
        t.save()
        response = self.client.get(reverse("index"))

        self.assertContains(
            response,
            # The unit test fails because this line is incorrect!
            # The test should continue to fail until issue #123 is resolved
            "I am currently hosted on Unknown Host and I am moving to Google Cloud!",
        )


class TestCloudsurfPage(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        user = User.objects.create(username="newtestuser")
        user.set_password("12345")
        user.save()
        self.client.login(username="newtestuser", password="12345")
        populate()

    @classmethod
    def tearDownClass(cls):
        User.objects.filter(username="newtestuser").delete()
        super().tearDownClass()

    def test_index_page_renders(self):
        response = self.client.get(reverse("CloudSurf"), follow=True)
        self.assertContains(response, "CloudSurf")

    def test_cloudsurf_page_contains_link_to_index_page(self):
        response = self.client.get(reverse("CloudSurf"), follow=True)
        self.assertContains(
            response, '<a class="nav-link" href="/">Home</a>', html=True
        )

    def test_cloudsurf_page_displays_links_dynamically(self):
        new_provider = API.objects.get_or_create(
            name="azure", long_name="Microsoft Azure", is_provider=True
        )[0]
        new_api = API.objects.get_or_create(
            name="duck", long_name="Duck DNS", is_provider=False
        )[0]
        new_provider.save()
        new_api.save()
        response = self.client.get(reverse("CloudSurf"), follow=True)
        # This test isn't perfect but this isn't crucial
        self.assertContains(
            response,
            '<a class="btn btn-primary cloudsurf azure" href="/azure/">CloudSurf to Microsoft Azure</a>',
            html=True,
        )


class TestUtils(TestCase):
    def test_get_current_host_fails_when_population_script_not_run(self):
        from .utils_host import get_current_cloud_host
        from django.core.exceptions import ImproperlyConfigured

        with self.assertRaises(ImproperlyConfigured):
            get_current_cloud_host()


class TestModelsFundamentals(TestCase):
    # test that the api model allows instances to be created as expected
    def test_api_model(self):
        new_provider = API.objects.get_or_create(
            name="azure", long_name="Microsoft Azure", is_provider=True
        )[0]
        new_api = API.objects.get_or_create(
            name="duck", long_name="Duck DNS", is_provider=False
        )[0]
        self.assertEqual(new_provider.name, "azure")
        self.assertEqual(new_provider.long_name, "Microsoft Azure")
        self.assertTrue(new_provider.is_provider)
        self.assertEqual(new_api.name, "duck")
        self.assertEqual(new_api.long_name, "Duck DNS")
        self.assertFalse(new_api.is_provider)

    # test that the key model allows instances to be created as expected and
    # that foreign key works correctly with the api model
    def test_key_model(self):
        # create an instance of keys and check is as expected
        new_provider = API.objects.get_or_create(
            name="google", long_name="Google Cloud", is_provider=True
        )[0]
        new_provider.save()
        new_key = Key.objects.get_or_create(
            name="secret",
            value="6c27e3be-9afd-478d-bcf9-5ed3a0b23b3e",
            provider=new_provider,
        )[0]
        new_key.save()
        # check that the FK is assigned properly for the key
        self.assertEqual(new_provider, new_key.provider)
        self.assertEqual(new_key.name, "secret")
        self.assertEqual(new_key.value, "6c27e3be-9afd-478d-bcf9-5ed3a0b23b3e")
        self.assertIn(str(new_key), "secret for Google Cloud")

    # Test that the transition model allows instances to be created as expected
    # and links with the api model correctly
    def test_transition_model(self):
        new_provider_start = API.objects.get_or_create(
            name="aws", long_name="Amazon web Services", is_provider=True
        )[0]
        new_provider_start.save()
        new_provider_end = API.objects.get_or_create(
            name="azure", long_name="Microsoft Azure", is_provider=True
        )[0]
        new_provider_end.save()
        time_now = timezone.now()
        user = User.objects.create_user("John")
        t = Transition.objects.get_or_create(
            user=user,
            start_time=time_now,
            start_provider=new_provider_start,
            end_provider=new_provider_end,
        )[0]
        t.end_time = time_now
        t.save()
        self.assertEqual(t.end_time, time_now)
        self.assertEqual(t.start_provider, new_provider_start)
        self.assertEqual(t.end_provider, new_provider_end)
        # test that field holding the time and user have entries
        assert t.start_time is not None
        assert t.user is not None

    def test_transition_exists_after_user_responsible_deleted(self):
        # create a user
        # create a transition done by that user
        # delete the user
        # check that the transition is still there

        start = API.objects.get_or_create(name="google", is_provider=True)[0]
        start.save()
        end = API.objects.get_or_create(name="azure", is_provider=True)[0]
        end.save()
        time_now = timezone.now()
        new_user = User.objects.create_user("Aidan")
        t = Transition.objects.get_or_create(user=new_user)[0]
        t.end_time = time_now
        t.start_provider = start
        t.end_provider = end
        t.save()
        User.objects.filter(username="Aidan").delete()
        # get the object in transition and see if it exists
        exists = Transition.objects.filter(end_time=time_now).count()
        self.assertTrue(exists == 1)

    def test_model_strings(self):
        start = API.objects.get_or_create(name="google", is_provider=True)[0]
        start.save()
        self.assertEquals(str(start), start.long_name)
        populate()
        azure = API.objects.get(name="azure")
        time_now = timezone.now()
        t = Transition.objects.get_or_create(
            user=None,
            start_time=time_now,
            end_time=None,
            start_provider=azure,
            end_provider=start,
        )[0]
        self.assertIn(azure.long_name + " to " + start.long_name, str(t))


class PlaybookUtilsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        user = User.objects.create(username="newtestuser")
        user.set_password("12345")
        user.save()
        self.client.login(username="newtestuser", password="12345")
        populate()

    @classmethod
    def tearDownClass(cls):
        User.objects.filter(username="newtestuser").delete()
        super().tearDownClass()

    def test_cloudsurf_creates_appropriate_transition(self):
        goog = API.objects.get(name="google", is_provider=True)
        move_self(target=goog)
        latest_transition = Transition.objects.latest("start_time")
        self.assertIs(latest_transition.end_time, None)
        self.assertEqual(latest_transition.end_provider, goog)

    def test_cloudsurf_fails_if_target_invalid(self):
        with self.assertRaises(ValueError):
            move_self(target="fork")

    def test_transition_will_not_run_twice(self):
        populate()
        start = API.objects.get_or_create(name="google", is_provider=True)[0]
        start.save()
        end = API.objects.get_or_create(name="azure", is_provider=True)[0]
        end.save()
        move_self(target=end)
        self.assertRaises(CloudSurfAlreadyInProgressException, move_self, target=end)

    def test_cloudsurfing_twice_will_fail(self):
        first_google = self.client.get(reverse("google"), follow=True)
        self.assertContains(first_google, "Moving to")
        second_google = self.client.get(reverse("azure"), follow=True)
        self.assertContains(
            second_google,
            "Failed to move to Microsoft Azure because a CloudSurf is already in progress",
        )

    # unfortunately this cannot be tested properly due to there being no way to simulate the current cloud host
    # See issue #155
    def test_that_cannot_transition_to_current_host(self):
        pass


class TemplateTagsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        user = User.objects.create(username="newtestuser")
        user.set_password("12345")
        user.save()
        self.client.login(username="newtestuser", password="12345")
        populate()

    @classmethod
    def tearDownClass(cls):
        User.objects.filter(username="newtestuser").delete()
        super().tearDownClass()

    def render_template(self, template_string, context=None):
        context = context or {}
        context = Context(context)
        return Template(template_string).render(context)

    # need to change this as
    def test_heading_staying_put(self):
        running_time = "5 hours"
        current_provider = "google"
        end_provider = None
        response = self.render_template(
            "{% load leidoscloud_template_tags %}{% heading_text current_provider running_time end_provider %}",
            {
                "current_provider": current_provider,
                "running_time": running_time,
                "end_provider": end_provider,
            },
        )
        self.assertInHTML(
            "<h1>I am currently hosted on Google and have been for 5 hours!</h1>",
            response,
        )

    def test_heading_moving(self):
        # test the index page for each situation - moving, staying put on cloud
        # and initial launch
        populate()

        azure = API.objects.get(name="azure")
        google_cloud = API.objects.get(name="google")
        response = self.client.get(reverse("index"), follow=True)
        # create transitions for moving, staying put and initial launch - doesnt exist
        time_now = timezone.now()
        user = User.objects.create_user("John")
        t = Transition.objects.get_or_create(
            user=user,
            start_time=time_now,
            end_time=None,
            start_provider=azure,
            end_provider=google_cloud,
        )[0]
        t.save()

        Transition.objects.latest("start_time")

        response = self.client.get(reverse("index"), follow=True)

        self.assertInHTML(
            "<h1>I am currently hosted on Unknown Host and I am moving to Google Cloud!</h1>",
            str(response.content),
        )

    def test_heading_no_transitions(self):
        populate()

        response = self.client.get(reverse("index"), follow=True)
        self.assertContains(
            response,
            "I am currently hosted on Unknown Host and  have been for eternity and/or never!",
        )

    def test_link(self):
        # This can no longer be easily unit tested because the current tag is very
        # difficult to test
        pass

    def test_table(self):
        # create entries in the Transition table and check that they are
        # rendered correctly
        populate()
        user = User.objects.create_user("Aidan")
        azure = API.objects.get(name="azure")
        google_cloud = API.objects.get(name="google")
        time = timezone.now()
        t = Transition.objects.get_or_create(
            user=user,
            start_time=time,
            end_time=time,
            start_provider=azure,
            end_provider=google_cloud,
        )[0]
        t.save()
        response = self.client.get(reverse("index"), follow="True")

        # test the headings and data fields ar correct
        self.assertInHTML(
            '<th scope="col">user</th>', str(response.content),
        )

        self.assertInHTML(
            '<th scope="col">start_provider</th>', str(response.content),
        )

        self.assertInHTML(
            '<th scope="col">end_provider</th>', str(response.content),
        )

        self.assertInHTML(
            '<th scope="col">succeeded</th>', str(response.content),
        )

        self.assertInHTML(
            "<td>Aidan</td>", str(response.content),
        )

        self.assertInHTML(
            "<td>Google Cloud</td>", str(response.content),
        )

        self.assertInHTML(
            "  <td>Microsoft Azure</td>", str(response.content),
        )

        self.assertInHTML(
            "  <td>False</td>", str(response.content),
        )


class TestUtilsStockAPI(TestCase):
    def test_provider_objects(self):
        alpha_vantage = API.objects.get_or_create(
            name="AlphaVantage", long_name="Alpha Vantage", is_provider=False
        )[0]
        alpha_key = Key.objects.get_or_create(
            name="key",
            value="6c27e3be-9afd-478d-bcf9-5ed3a0b23b3e",
            provider=alpha_vantage,
        )[0]
        google = API.objects.get_or_create(
            name="google",
            long_name="Google Cloud",
            ticker_symbol="GOOG",
            is_provider=True,
        )[0]
        alpha_vantage.save()
        google.save()
        alpha_key.save()
        alpha, provider_objects = utils_stock_api.get_provider_api()
        retrieved_key = utils_stock_api.get_api_key(alpha)
        self.assertEqual(alpha_vantage, alpha)
        self.assertEqual(google, provider_objects[0])
        self.assertEqual(retrieved_key, alpha_key.value)


class TestKeyAlert(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        user = User.objects.create(username="newtestuser")
        user.set_password("12345")
        user.save()
        self.client.login(username="newtestuser", password="12345")

    @classmethod
    def tearDownClass(cls):
        User.objects.filter(username="newtestuser").delete()
        super().tearDownClass()

    def test_not_populating_shows_alert(self):
        from django.core.exceptions import ImproperlyConfigured

        with self.assertRaises(ImproperlyConfigured):
            response = self.client.get(reverse("index"), follow=True)
            self.assertContains(
                response,
                "You don't have all necessary keys in your database. The program will not work! Please enter all "
                "needed keys in the admin page.",
            )

    def test_missing_keys_shows_alert(self):
        populate()
        response = self.client.get(reverse("index"), follow=True)
        self.assertContains(
            response, " Please enter all needed keys in the admin page."
        )

    def test_having_keys_hides_alert(self):
        populate()
        aws = API.objects.filter(name="aws")[0]
        azure = API.objects.filter(name="azure")[0]
        duck = API.objects.filter(name="DuckDNS")[0]
        av = API.objects.filter(name="AlphaVantage")[0]

        # Check for duck key
        duck_token = Key.objects.get(provider=duck, name="token")
        duck_token.value = "asdf"
        duck_token.save()

        # Check for azure keys
        azure_token = Key.objects.get(provider=azure, name="subscription_id")
        azure_token.value = "asdf"
        azure_token.save()
        azure_token = Key.objects.get(provider=azure, name="client_id")
        azure_token.value = "asdf"
        azure_token.save()
        azure_token = Key.objects.get(provider=azure, name="tenant")
        azure_token.value = "asdf"
        azure_token.save()
        azure_token = Key.objects.get(provider=azure, name="secret")
        azure_token.value = "asdf"
        azure_token.save()

        # Check for AWS keys
        aws_token = Key.objects.get(provider=aws, name="secret_key")
        aws_token.value = "asdf"
        aws_token.save()
        aws_token = Key.objects.get(provider=aws, name="access_key")
        aws_token.value = "asdf"
        aws_token.save()

        # Check for AlphaVantage key
        av_token = Key.objects.get(provider=av, name="key")
        av_token.value = "asdf"
        av_token.save()

        response = self.client.get(reverse("index"), follow=True)
        self.assertNotContains(
            response, " Please enter all needed keys in the admin page."
        )


class TestFullLog(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        user = User.objects.create(username="newtestuser")
        user.set_password("12345")
        user.save()
        self.client.login(username="newtestuser", password="12345")
        populate()

    @classmethod
    def tearDownClass(cls):
        User.objects.filter(username="newtestuser").delete()
        super().tearDownClass()

    def test_delete_log_full_and_main_log_empty(self):
        ran = "".join(
            [random.choice(string.ascii_letters + string.digits) for n in range(32)]
        )
        if Path(DELETE_LOG_TXT).exists():
            os.remove(DELETE_LOG_TXT)
        with open(DELETE_LOG_TXT, "w+") as f:
            f.write(ran)
            # write to the file
        # check that it is in teh response
        response = self.client.get(reverse("delete_log"))
        self.assertContains(response, ran)
        if Path(MAIN_LOG_TXT).exists():
            os.remove(MAIN_LOG_TXT)
        response = self.client.get(reverse("log"))
        self.assertContains(response, "Failed to open with")

    def test_main_log_full_and_delete_log_empty(self):
        ran = "".join(
            [random.choice(string.ascii_letters + string.digits) for n in range(32)]
        )
        if Path(MAIN_LOG_TXT).exists():
            os.remove(MAIN_LOG_TXT)
        with open(MAIN_LOG_TXT, "w+") as f:
            f.write(ran)
        response = self.client.get(reverse("log"))
        self.assertContains(response, ran)
        if Path(DELETE_LOG_TXT).exists():
            os.remove(DELETE_LOG_TXT)
        response = self.client.get(reverse("delete_log"))
        self.assertContains(response, "Failed to open with")

    def test_task_appears_high_in_file(self):
        if Path(MAIN_LOG_TXT).exists():
            os.remove(MAIN_LOG_TXT)
        with open(MAIN_LOG_TXT, "w+") as f:
            f.write(
                "2020-01-17 17:02:11,307 p=miles u=14825 | ok: [localhost]\n2020-01-17 17:02:11,326 p=miles u=14825 | "
                "TASK [Load in the SSH public key]\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd"
                "\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd"
                "\nasdf\nasd\nasdf\nasdfffffffffffffffff "
            )
        response = self.client.get(reverse("status"))
        self.assertContains(response, "Load in the SSH public key")

    def test_task_appears_last_line(self):
        if Path(MAIN_LOG_TXT).exists():
            os.remove(MAIN_LOG_TXT)
        with open(MAIN_LOG_TXT, "w+") as f:
            f.write(
                "2020-01-17 17:02:11,307 p=miles u=14825 | ok: [localhost]\n2020-01-17 17:02:11,326 p=miles u=14825 | "
                "TASK [Load in the SSH public key]\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd"
                "\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd"
                "\nasdf\nasd\nasdf\nasdfffffffffffffffff\n2020-01-17 17:02:10,291 p=miles u=14825 | TASK [Load in the "
                "SSH private key] "
            )
        response = self.client.get(reverse("status"))
        self.assertContains(response, "Load in the SSH private key")

    def test_task_appears_second_to_last(self):
        if Path(MAIN_LOG_TXT).exists():
            os.remove(MAIN_LOG_TXT)
        with open(MAIN_LOG_TXT, "w+") as f:
            f.write(
                "2020-01-17 17:02:11,307 p=miles u=14825 | ok: [localhost]\n2020-01-17 17:02:11,326 p=miles u=14825 | "
                "TASK [Load in the SSH public key]\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd"
                "\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd"
                "\nasdf\nasd\nasdf\nasdfffffffffffffffff\n2020-01-17 17:02:10,291 p=miles u=14825 | TASK [Load in the "
                "SSH private key]\na\n\n\n\n "
            )
        response = self.client.get(reverse("status"))
        self.assertContains(response, "Load in the SSH private key")

    def test_no_task_name(self):
        if Path(MAIN_LOG_TXT).exists():
            os.remove(MAIN_LOG_TXT)
        with open(MAIN_LOG_TXT, "w+") as f:
            f.write(
                "2020-01-17 17:02:11,307 p=miles u=14825 | ok: [localhost]\n2020-01-17 17:02:11,326 p=miles u=14825 | "
                "TASK [Load in the SSH public key]\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd"
                "\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd"
                "\nasdf\nasd\nasdf\nasdfffffffffffffffff\n2020-01-17 17:02:10,291 p=miles u=14825 | TASK []\na\n\n\n\n "
            )
        response = self.client.get(reverse("status"))
        self.assertContains(response, '"status": ""')

    def test_invalid_task_name(self):
        if Path(MAIN_LOG_TXT).exists():
            os.remove(MAIN_LOG_TXT)
        with open(MAIN_LOG_TXT, "w+") as f:
            f.write(
                "2020-01-17 17:02:11,307 p=miles u=14825 | ok: [localhost]\n2020-01-17 17:02:11,326 p=miles u=14825 | "
                "TASK [Load in the SSH public key]\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd"
                "\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd"
                "\nasdf\nasd\nasdf\nasdfffffffffffffffff\n2020-01-17 17:02:10,291 p=miles u=14825 | TASK [broken "
                "respon\naasdfasdf\nasdkjflasf\n\n\n "
            )
        response = self.client.get(reverse("status"))
        self.assertContains(response, '"status": "broken respon')

    def test_really_broken_task_name(self):
        if Path(MAIN_LOG_TXT).exists():
            os.remove(MAIN_LOG_TXT)
        with open(MAIN_LOG_TXT, "w+") as f:
            f.write(
                "2020-01-17 17:02:11,307 p=miles u=14825 | ok: [localhost]\n2020-01-17 17:02:11,326 p=miles u=14825 | "
                "TASK [Load in the SSH public key]\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd"
                "\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd"
                "\nasdf\nasd\nasdf\nasdfffffffffffffffff\n2020-01-17 17:02:10,291 p=miles u=14825 | TASK broken "
                "respon\naasdfasdf\nasdkjflasf\n\n\n "
            )
        response = self.client.get(reverse("status"))
        # Should print the entire line
        self.assertContains(
            response,
            '"status": "2020-01-17 17:02:10,291 p=miles u=14825 | TASK broken respon',
        )

    def test_totally_wrong_file(self):
        ran = "".join(
            [random.choice(string.ascii_letters + string.digits) for n in range(32)]
        )
        if Path(MAIN_LOG_TXT).exists():
            os.remove(MAIN_LOG_TXT)
        with open(MAIN_LOG_TXT, "w+") as f:
            f.write(ran)
        response = self.client.get(reverse("status"))
        self.assertContains(
            response, '{"error": "Invalid ansible log. Check entire log for details"}'
        )

    def test_copy_self_to_server_timings(self):
        if Path(MAIN_LOG_TXT).exists():
            os.remove(MAIN_LOG_TXT)
        with open(MAIN_LOG_TXT, "w+") as f:
            f.write(
                "2020-01-17 17:02:11,307 p=miles u=14825 | ok: [localhost]\n2020-01-17 17:02:11,326 p=miles u=14825 | "
                "TASK [Copying self to server]\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd"
                "\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd"
                "\nasdf\nasd\nasdf\nasdfffffffffffffffff "
            )
        response = self.client.get(reverse("status"))
        self.assertContains(response, '"status": "Not CloudSurfing"')
        # Check the correct time appears
        self.assertContains(response, str(datetime.now())[11:16])
        if Path(MAIN_LOG_TXT).exists():
            os.remove(MAIN_LOG_TXT)
        with open(MAIN_LOG_TXT, "w+") as f:
            f.write(
                "2020-01-17 17:02:11,307 p=miles u=14825 | ok: [localhost]\n2021-01-17 17:02:11,326 p=miles u=14825 | "
                "TASK [Copying self to server]\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd"
                "\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd\nasdf\nasd"
                "\nasdf\nasd\nasdf\nasdfffffffffffffffff "
            )
        response = self.client.get(reverse("status"))
        self.assertContains(response, '"status": "Copying self to server"')
        self.assertContains(response, "2021-01-17T17:02:01")


class TestLoginFunctionality(TestCase):
    def test_logged_in_user_sees_secret_nav_items(self):
        user = User.objects.create(username="testuser")
        user.set_password("12345")
        user.save()

        self.client.login(username="testuser", password="12345")
        response = self.client.get(reverse("CloudSurf"), follow=True)
        self.assertContains(response, "Log Out")

    def test_logged_out_user_cant_see_secret_nav_items(self):
        self.client.login(username="notauser", password="12345")
        response = self.client.get(reverse("index"), follow=True)
        self.assertNotContains(response, "Log Out")

    def test_login_works(self):
        user = User.objects.create(username="testuser")
        user.set_password("12345")
        user.save()
        logged_in = self.client.login(username="testuser", password="12345")
        self.assertTrue(logged_in)

    def test_login_doesnt_work(self):
        logged_in = self.client.login(username="notauser", password="12345")
        self.assertFalse(logged_in)

    def test_logged_out_correctly(self):
        logged_out = self.client.logout()
        self.assertFalse(logged_out)


# Create tests that check users cannot access restricted pages unless they are logged
# If they attempt this they should be redirected to the login page
class TestLoginRestrictions(TestCase):
    def test_index_page_not_showing_if_not_logged_in(self):
        response = self.client.get(reverse("index"), follow=True)
        self.assertContains(response, "Login", html=True)

    def test_cloudsurf_page_not_showing_if_not_logged_in(self):
        response = self.client.get(reverse("CloudSurf"), follow=True)
        self.assertContains(response, "Login", html=True)

    def test_cannot_manually_visit_aws_page(self):
        response = self.client.get(reverse("aws"), follow=True)
        self.assertContains(response, "Login", html=True)

    def test_cannot_manually_visit_google_page(self):
        response = self.client.get(reverse("google"), follow=True)
        self.assertContains(response, "Login", html=True)

    def test_cannot_manually_visit_azure_page(self):
        response = self.client.get(reverse("azure"), follow=True)
        self.assertContains(response, "Login", html=True)

    def test_cannot_manually_visit_log_page(self):
        response = self.client.get(reverse("log"), follow=True)
        self.assertContains(response, "Login", html=True)

    def test_cannot_manually_visit_delete_log_page(self):
        response = self.client.get(reverse("delete_log"), follow=True)
        self.assertContains(response, "Login", html=True)

    def test_cannot_manually_visit_status_page(self):
        response = self.client.get(reverse("status"), follow=True)
        self.assertContains(response, "Login", html=True)


class TestPredictions(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        user = User.objects.create(username="newtestuser")
        user.set_password("12345")
        user.save()
        self.client.login(username="newtestuser", password="12345")
        populate()

    @classmethod
    def tearDownClass(cls):
        User.objects.filter(username="newtestuser").delete()
        super().tearDownClass()

    # Test that save_stock_data function in utils saves to StockData table correctly
    def test_save_stock_data_function(self):
        # write to the table and check that it saves the record correctly
        stock_dict = {"google": 1.0, "azure": 2.0, "aws": 3.0}
        save_stock_data(stock_dict)
        stock = StockData.objects.get(
            google=stock_dict["google"],
            azure=stock_dict["azure"],
            aws=stock_dict["aws"],
        )
        self.assertEqual(stock.google, 1.0)
        self.assertEqual(stock.azure, 2.0)
        self.assertEqual(stock.aws, 3.0)

    # Test that the correct prediction is generated from the stock data by save_best_prediction
    def test_save_best_prediction_function(self):
        # Test that the correct provider is chosen based on the stock data
        for i in range(10):
            stock_dict = {"google": 1.0, "azure": 1.5, "aws": 2.0}
            save_stock_data(stock_dict)
        # call the prediction function which will save the prediction to the Prediction table
        save_best_prediction()
        # the lowest average share price should be google, so this provider should be predicted
        prediction = Prediction.objects.latest("time")
        self.assertEqual(prediction.provider.name, "google")
