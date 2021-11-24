import pulumi
import pulumi_azure_native as azure_native
from pulumi import ResourceOptions


class VMLinuxArgs:
    def __init__(self, resource_group, workspace_id, workspace_key, admin_user, admin_ssh_pubkey, subnet_id,
                 source_address_prefix):
        self.resource_group = resource_group
        self.workspace_id = workspace_id
        self.workspace_key = workspace_key
        self.admin_user = admin_user
        self.admin_ssh_pubkey = admin_ssh_pubkey
        self.subnet_id = subnet_id
        self.source_address_prefix = source_address_prefix


class VMLinux(pulumi.ComponentResource):
    def __init__(self,
                 name: str,
                 args: VMLinuxArgs,
                 opts: ResourceOptions = None):
        super().__init__("towe:modules:VMLinux", name, {}, opts)

        child_opts = ResourceOptions(parent=self)

        self.public_ip_address = azure_native.network.PublicIPAddress(
            name,
            location=args.resource_group.location,
            public_ip_address_name=f"pip-{name}",
            resource_group_name=args.resource_group.name,
            opts=ResourceOptions(parent=self))

        self.network_security_group = azure_native.network.NetworkSecurityGroup(
            name,
            location=args.resource_group.location,
            network_security_group_name=f"nsg-{name}",
            resource_group_name=args.resource_group.name,
            security_rules=[
                azure_native.network.SecurityRuleArgs(
                    access="Allow",
                    destination_address_prefix="*",
                    destination_port_range="22",
                    direction="Inbound",
                    name="ssh",
                    priority=100,
                    protocol="*",
                    source_address_prefix=args.source_address_prefix,
                    source_port_range="*",
                ),
                azure_native.network.SecurityRuleArgs(
                    access="Allow",
                    destination_address_prefix="*",
                    destination_port_range="80",
                    direction="Inbound",
                    name="http",
                    priority=101,
                    protocol="*",
                    source_address_prefix=args.source_address_prefix,
                    source_port_range="*",
                )
            ],
            opts=ResourceOptions(parent=self)
        )

        self.network_interface = azure_native.network.NetworkInterface(
            name,
            enable_accelerated_networking=True,
            ip_configurations=[{
                "name": "ipconfig1",
                "publicIPAddress": azure_native.network.PublicIPAddressArgs(
                    id=self.public_ip_address.id,
                ),
                "subnet": azure_native.network.SubnetArgs(
                    id=args.subnet_id,
                ),
            }],
            network_security_group=azure_native.network.NetworkSecurityGroupArgs(
                id=self.network_security_group.id,
            ),
            location=args.resource_group.location,
            network_interface_name=f"nic-{name}",
            resource_group_name=args.resource_group.name,
            opts=ResourceOptions(parent=self.public_ip_address)
        )

        self.virtual_machine = azure_native.compute.VirtualMachine(
            name,
            vm_name=name,
            hardware_profile=azure_native.compute.HardwareProfileArgs(
                vm_size="Standard_D2s_v3",
            ),
            location=args.resource_group.location,
            network_profile=azure_native.compute.NetworkProfileArgs(
                network_interfaces=[
                    azure_native.compute.NetworkInterfaceReferenceArgs(
                        id=self.network_interface.id,
                        primary=True,
                    )],
            ),
            os_profile=azure_native.compute.OSProfileArgs(
                admin_username=args.admin_user,
                computer_name=name,
                linux_configuration=azure_native.compute.LinuxConfigurationArgs(
                    patch_settings=azure_native.compute.LinuxPatchSettingsArgs(
                        patch_mode="ImageDefault",
                    ),
                    provision_vm_agent=True,
                    disable_password_authentication=True,
                    ssh=azure_native.compute.SshConfigurationArgs(
                        public_keys=[
                            azure_native.compute.SshPublicKeyArgs(
                                key_data=args.admin_ssh_pubkey,
                                path="/home/%s/.ssh/authorized_keys" % args.admin_user,
                            )],
                    ),
                ),
            ),
            resource_group_name=args.resource_group.name,
            storage_profile=azure_native.compute.StorageProfileArgs(
                image_reference=azure_native.compute.ImageReferenceArgs(
                    offer="CentOS-LVM",
                    publisher="OpenLogic",
                    sku="8-lvm-gen2",
                    version="latest",
                ),
                os_disk=azure_native.compute.OSDiskArgs(
                    caching="ReadWrite",
                    create_option="FromImage",
                    managed_disk=azure_native.compute.ManagedDiskParametersArgs(
                        storage_account_type="Premium_LRS",
                    ),
                    name=f"disk-{name}",
                )
            ),
            opts=ResourceOptions(parent=self.network_interface))

        self.vm_monitoring = azure_native.compute.VirtualMachineExtension(
            name,
            vm_name=self.virtual_machine.name,
            resource_group_name=args.resource_group.name,
            publisher="Microsoft.EnterpriseCloud.Monitoring",
            type="OmsAgentForLinux",
            type_handler_version="1.13",
            auto_upgrade_minor_version=True,
            settings={
                "workspaceId": args.workspace_id
            },
            protected_settings={
                "workspaceKey": args.workspace_key
            },
            opts=ResourceOptions(parent=self.virtual_machine)
        )

        self.register_outputs({})
