from typing import Any, Mapping

import pulumi
import pulumi_azure_native as azure_native
from pulumi import ResourceOptions


# Turn `<id>` into `{ <id>: {} }`
def id_to_dict(id_output) -> Mapping[str, Any]:
    my_dict = {id_output: {}}
    return my_dict


class UpdateManagementArgs:
    def __init__(self, resource_group, retention_in_days):
        self.resource_group = resource_group
        self.retention_in_days = retention_in_days


class UpdateManagement(pulumi.ComponentResource):
    def __init__(self,
                 name: str,
                 args: UpdateManagementArgs,
                 opts: ResourceOptions = None):
        super().__init__("towe:modules:UpdateManagement", name, {}, opts)

        child_opts = ResourceOptions(parent=self)

        self.automation_user_identity = azure_native.managedidentity.UserAssignedIdentity(
            f"id-{name}",
            location=args.resource_group.location,
            resource_group_name=args.resource_group.name,
            opts=ResourceOptions(parent=self)
        )

        self.automation_account = azure_native.automation.AutomationAccount(
            name,
            automation_account_name=f"aa-{name}",
            location=args.resource_group.location,
            resource_group_name=args.resource_group.name,
            sku=azure_native.automation.SkuArgs(
                name="Basic",
            ),
            identity=azure_native.automation.IdentityArgs(
                type="UserAssigned",
                user_assigned_identities=self.automation_user_identity.id.apply(id_to_dict)
            ),
            opts=ResourceOptions(parent=self)
        )

        self.log_analytics = azure_native.operationalinsights.Workspace(
            name,
            workspace_name=f"law-{name}",
            location=args.resource_group.location,
            resource_group_name=args.resource_group.name,
            retention_in_days=args.retention_in_days,
            sku=azure_native.operationalinsights.WorkspaceSkuArgs(
                name="PerGB2018",
            ),
            opts=ResourceOptions(parent=self)
        )

        self.automation_linked_service = azure_native.operationalinsights.LinkedService(
            name,
            linked_service_name="automation",  # name is important
            resource_group_name=args.resource_group.name,
            workspace_name=self.log_analytics.name,
            write_access_resource_id=self.automation_account.id,
            opts=ResourceOptions(parent=self.log_analytics)
        )

        self.automation_update_solution = azure_native.operationsmanagement.Solution(
            name,
            solution_name=self.log_analytics.name.apply(lambda name: f"Updates({name})"),  # name is important
            location=args.resource_group.location,
            resource_group_name=args.resource_group.name,
            plan=azure_native.operationsmanagement.SolutionPlanArgs(
                name="Updates",
                product="OMSGallery/Updates",
                publisher="Microsoft",
                promotion_code=""
            ),
            properties=azure_native.operationsmanagement.SolutionPropertiesArgs(
                workspace_resource_id=self.log_analytics.id,
            ),
            opts=ResourceOptions(parent=self.log_analytics)
        )

        self.register_outputs({})
