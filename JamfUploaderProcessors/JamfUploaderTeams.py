#!/usr/local/autopkg/python

"""
Copyright 2022 Graham Pugh

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import json
import os.path
import sys

from time import sleep
from autopkglib import ProcessorError  # pylint: disable=import-error

# to use a base module in AutoPkg we need to add this path to the sys.path.
# this violates flake8 E402 (PEP8 imports) but is unavoidable, so the following
# imports require noqa comments for E402
sys.path.insert(0, os.path.dirname(__file__))

from JamfUploaderLib.JamfUploaderBase import JamfUploaderBase  # noqa: E402


__all__ = ["JamfUploaderTeams"]


class JamfUploaderTeams(JamfUploaderBase):
    description = (
        "Posts to Teams via webhook based on output of a JamfPolicyUploader process. "
    )
    input_variables = {
        "JSS_URL": {"required": False, "description": ("JSS_URL.")},
        "POLICY_CATEGORY": {"required": False, "description": ("Policy Category.")},
        "PKG_CATEGORY": {"required": False, "description": ("Package Category.")},
        "policy_name": {
            "required": False,
            "description": ("Untested product name from a jamf recipe."),
        },
        "NAME": {"required": False, "description": ("Generic product name.")},
        "pkg_name": {"required": False, "description": ("Package in policy.")},
        "jamfpackageuploader_summary_result": {
            "required": False,
            "description": ("Summary results of package processors."),
        },
        "jamfpolicyuploader_summary_result": {
            "required": False,
            "description": ("Summary results of policy processors."),
        },
        "teams_webhook_url": {"required": True, "description": ("Teams webhook.")},
    }
    output_variables = {}

    __doc__ = description

    def teams_status_check(self, r):
        """Return a message dependent on the HTTP response"""
        if r.status_code == 200 or r.status_code == 201:
            self.output("Teams webhook sent successfully")
            return "break"
        else:
            self.output("WARNING: Teams webhook failed to send")
            self.output(r.output, verbose_level=2)

    def main(self):
        """Do the main thing"""
        jss_url = self.env.get("JSS_URL")
        policy_category = self.env.get("POLICY_CATEGORY")
        category = self.env.get("PKG_CATEGORY")
        policy_name = self.env.get("policy_name")
        name = self.env.get("NAME")
        version = self.env.get("version")
        pkg_name = self.env.get("pkg_name")
        jamfpackageuploader_summary_result = self.env.get(
            "jamfpackageuploader_summary_result"
        )
        jamfpolicyuploader_summary_result = self.env.get(
            "jamfpolicyuploader_summary_result"
        )

        teams_webhook_url = self.env.get("teams_webhook_url")

        selfservice_policy_name = name
        self.output(f"JSS address: {jss_url}")
        self.output(f"Title: {selfservice_policy_name}")
        self.output(f"Policy: {policy_name}")
        self.output(f"Version: {version}")
        self.output(f"Package: {pkg_name}")
        self.output(f"Package Category: {category}")
        self.output(f"Policy Category: {policy_category}")

        if jamfpackageuploader_summary_result and jamfpolicyuploader_summary_result:
            teams_text = (
                f"URL: {jss_url}\n"
                + f"Title: *{selfservice_policy_name}*\n"
                + f"Version: *{version}*\n"
                + f"Category: *{category}*\n"
                + f"Policy Name: *{policy_name}*\n"
                + f"Package: *{pkg_name}*"
            )
        elif jamfpolicyuploader_summary_result:
            teams_text = (
                f"URL: {jss_url}\n"
                + f"Title: *{selfservice_policy_name}*\n"
                + f"Category: *{category}*\n"
                + f"Policy Name: *{policy_name}*\n"
                + "No new package uploaded"
            )
        elif jamfpackageuploader_summary_result:
            teams_text = (
                f"URL: {jss_url}\n"
                + f"Version: *{version}*\n"
                + f"Category: *{category}*\n"
                + f"Package: *{pkg_name}*"
            )
        else:
            self.output("Nothing to report to Teams")
            return

        teams_data = {
            "text": teams_text,
            "title": "New Item uploaded to Jamf Pro"
        }

        teams_json = json.dumps(teams_data)

        count = 0
        while True:
            count += 1
            self.output(
                "Teams webhook post attempt {}".format(count), verbose_level=2,
            )
            r = self.curl(request="POST", url=teams_webhook_url, data=teams_json)
            # check HTTP response
            if self.teams_status_check(r) == "break":
                break
            if count > 5:
                self.output("Teams webhook send did not succeed after 5 attempts")
                self.output("\nHTTP POST Response Code: {}".format(r.status_code))
                raise ProcessorError("ERROR: Teams webhook failed to send")
            sleep(10)


if __name__ == "__main__":
    PROCESSOR = JamfUploaderTeams()
    PROCESSOR.execute_shell()
