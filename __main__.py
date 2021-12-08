import sys
import os
import json
import pulumi
from pulumi import automation as auto, ResourceOptions
import pulumi_azure_native as azure_native

import Shared
import VMs

from dotenv import load_dotenv
from pathlib import Path

dotenv_path = Path('dev.env')
load_dotenv(dotenv_path=dotenv_path)

admin_user = os.getenv('ADMIN_USER')
admin_ssh_pubkey = os.getenv('ADMIN_SSH_PUBKEY')
access_source_address_prefix = os.getenv('ACCESS_SOURCE_ADDRESS_PREFIX')


# This is the pulumi program in "inline function" form
def pulumi_program():
    # Declare management resources
    rg_management = azure_native.resources.ResourceGroup(resource_name=f"{stack_name}-mgmt")
    update_management = Shared.UpdateManagement(f"{stack_name}-mgmt", Shared.UpdateManagementArgs(
        resource_group=rg_management,
        retention_in_days=30
    ))
    pulumi.export("automation_account", pulumi.Output.all(update_management.automation_account.name))

    # Declare compute resources
    rg_compute = azure_native.resources.ResourceGroup(resource_name=stack_name)
    vnet_compute = azure_native.network.VirtualNetwork(
        "virtualNetwork",
        address_space=azure_native.network.AddressSpaceArgs(
            address_prefixes=["10.0.0.0/16"],
        ),
        subnets=[azure_native.network.SubnetArgs(
            address_prefix="10.0.0.0/16",
            name=stack_name,
        )],
        location=rg_compute.location,
        resource_group_name=rg_compute.name,
        virtual_network_name=stack_name)

    vm_cfgs = [
        {
            "name": stack_name + "01",
        }
    ]

    vm_output = []
    for vm_cfg in vm_cfgs:
        shared_keys = pulumi.Output.all(rg_management.name, update_management.log_analytics.name) \
            .apply(lambda args: azure_native.operationalinsights.get_shared_keys(
                resource_group_name=args[0],
                workspace_name=args[1]
            ))

        vm = VMs.VMLinux(vm_cfg['name'], VMs.VMLinuxArgs(
            resource_group=rg_compute,
            workspace_id=update_management.log_analytics.customer_id.apply(lambda cid: cid),
            workspace_key=shared_keys.primary_shared_key,
            admin_user=admin_user,
            admin_ssh_pubkey=admin_ssh_pubkey,
            subnet_id=vnet_compute.subnets[0].id,
            source_address_prefix=access_source_address_prefix
        ), opts=ResourceOptions(parent=vnet_compute))

        vm_output.append({
            "id": vm.virtual_machine.id,
            "name": vm.virtual_machine.name,
            "pip": vm.public_ip_address.ip_address
        })

    pulumi.export("vm_output", pulumi.Output.all(vm_output))


# To destroy our program, we can run python main.py destroy
destroy = False
# To preview our program, we can run python main.py preview
preview = False
args = sys.argv[1:]
if len(args) > 0:
    if args[0] == "destroy":
        destroy = True
    elif args[0] == "preview":
        preview = True

project_name = "update-management"
# We use a simple stack name here, but recommend using auto.fully_qualified_stack_name for maximum specificity.
stack_name = "dev"
# stack_name = auto.fully_qualified_stack_name("myOrgOrUser", project_name, stack_name)

# create or select a stack matching the specified name and project.
# this will set up a workspace with everything necessary to run our inline program (pulumi_program)
stack = auto.create_or_select_stack(stack_name=stack_name,
                                    project_name=project_name,
                                    program=pulumi_program)

print("successfully initialized stack")

# for inline programs, we must manage plugins ourselves
print("installing plugins...")
stack.workspace.install_plugin("azure-native", "v1.23.0")
print("plugins installed")

# set stack configuration specifying the Azure region to deploy
print("setting up config")
stack.set_config("azure-native:location", auto.ConfigValue(value=os.getenv('AZURE_LOCATION')))

print("config set")

print("refreshing stack...")
stack.refresh(on_output=print)
print("refresh complete")

if destroy:
    print("destroying stack...")
    stack.destroy(on_output=print)
    print("stack destroy complete")
    sys.exit()

if preview:
    print("stack preview")
    up_res = stack.preview(on_output=print)
    print(f"preview summary: \n{json.dumps(up_res.change_summary, indent=4)}")
    sys.exit()

print("updating stack...")
up_res = stack.up(on_output=print)
print(f"update summary: \n{json.dumps(up_res.summary.resource_changes, indent=4)}")
