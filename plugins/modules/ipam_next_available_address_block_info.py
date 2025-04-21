#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: Infoblox Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: ipam_next_available_address_block_info
short_description: Manage NextAvailableAddressBlock
description:
    - Manage NextAvailableAddressBlock
version_added: 2.0.0
author: Infoblox Inc. (@infobloxopen)
options:
    id:
        description:
            - ID of the object
        type: str
        required: false
    cidr:
        description:
            - The CIDR value of the object
        type: int
        required: true
    count:
        description:
            - Number of objects to generate. Default 1 if not set
        type: int
        required: false
        default: 1
    tag_filters:
        description:
            - Filter dict to filter objects by tags
        type: dict
        required: false
extends_documentation_fragment:
    - infoblox.universal_ddi.common
"""  # noqa: E501

EXAMPLES = r"""
    - name: "Create an Address Block"
      infoblox.universal_ddi.ipam_address_block:
        address: "10.0.0.0/16"
        space: "{{ ip_space.id }}"
        state: "present"

    - name: "Create an Address Block with tags"
      infoblox.universal_ddi.ipam_address_block:
        address: "192.168.0.0/16"
        space: "{{ ip_space.id }}"
        tags:
          environment: "production"
          location: "data-center-1"
        state: "present"

    - name: Get Next Available Address Block Information by ID
      infoblox.universal_ddi.ipam_next_available_address_block_info:
          id: "{{ address_block.id }}"
          cidr: 20

    - name: Get Next Available Address Block Information by ID and Count
      infoblox.universal_ddi.ipam_next_available_address_block_info:
        id: "{{ address_block.id }}"
        cidr: 24
        count: 5

    - name: Get Next Available Address Block Information by a single tag filter
      infoblox.universal_ddi.ipam_next_available_address_block_info:
        tag_filters:
          environment: "production"
        cidr: 24
        count: 5

    - name: Get Next Available Address Block Information by multiple tag filters
      infoblox.universal_ddi.ipam_next_available_address_block_info:
        tag_filters:
          environment: "production"
          location: "data-center-1"
        cidr: 24
        count: 10
"""

RETURN = r"""
id:
    description:
        - ID of the AddressBlock object.
    type: str
    returned: Always
objects:
    description:
        - List of next available address block's addresses.
    type: list
    elements: str
    returned: Always
"""

from ansible_collections.infoblox.universal_ddi.plugins.module_utils.modules import UniversalDDIAnsibleModule

try:
    from ipam import AddressBlockApi
    from universal_ddi_client import ApiException
except ImportError:
    pass  # Handled by UniversalDDIAnsibleModule


class NextAvailableAddressBlockInfoModule(UniversalDDIAnsibleModule):
    def __init__(self, *args, **kwargs):
        super(NextAvailableAddressBlockInfoModule, self).__init__(*args, **kwargs)
        self._existing = None
        self._limit = 1000

    def find(self):
        all_results = []
        offset = 0
        while True:
            try:
                resp = AddressBlockApi(self.client).list_next_available_ab(
                    id=self.params["id"], cidr=self.params["cidr"], count=self.params["count"]
                )
                all_results.extend(resp.results)

                if len(resp.results) < self._limit:
                    break
                offset += self._limit

            except ApiException as e:
                self.fail_json(msg=f"Failed to execute command: {e.status} {e.reason} {e.body}")

        return all_results

    def find_address_block(self, id=None, count=None):
        try:
            resp = AddressBlockApi(self.client).list_next_available_ab(id=id, cidr=self.params["cidr"], count=count)

            return resp.results
        except ApiException:
            return None

    def run_command(self):
        result = dict(objects=[])

        if self.check_mode:
            self.exit_json(**result)

        count = self.params["count"]

        # Validate count is within allowed range
        if not 1 <= count <= 20:
            self.fail_json(msg="count must be between 1 and 20.")

        if self.params["tag_filters"]:
            address_blocks = self.find_address_blocks_by_tags(self.params["tag_filters"])
            if not address_blocks:
                self.fail_json(msg="No address block found with the given tags.")

            find_results = []
            for ab in address_blocks:

                # Check if the address block have the free address block
                if count > 1:
                    check_result = self.find_address_block(id=ab.id, count=1)
                    if not check_result:
                        continue

                remaining_count = count - len(find_results)
                while len(find_results) < count:
                    find_result = self.find_address_block(id=ab.id, count=remaining_count)
                    if find_result:
                        find_results.extend(find_result)
                        break
                    else:
                        remaining_count -= 1
                        if not remaining_count:
                            break

            # Move the check for insufficient addresses outside of the loop
            if len(find_results) < count:
                self.fail_json(msg="Not enough address blocks found with the given tags.")

        else:
            find_results = self.find()

        result["objects"] = [r.address for r in find_results]
        self.exit_json(**result)


def main():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        id=dict(type="str", required=False),
        cidr=dict(type="int", required=True),
        count=dict(type="int", required=False, default=1),
        tag_filters=dict(type="dict", required=False),
    )

    module = NextAvailableAddressBlockInfoModule(
        argument_spec=module_args,
        supports_check_mode=True,
        required_one_of=[["id", "tag_filters"]],
        mutually_exclusive=[["id", "tag_filters"]],
    )
    module.run_command()


if __name__ == "__main__":
    main()
