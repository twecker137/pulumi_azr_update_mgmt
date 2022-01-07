# Azure AKS Linux Update Management Deployment

## Description

This is a simple example of an Azure AKS Linux Update Management deployment.
With this deployment, you can easily deploy some Linux VMs, create log analytics workspace, and monitor the VMs.
Also, there is an automation account created to be able to schedule the updates.

There is a template for assigning the appropriate environment variables: [env.template](env.template)

```shell
# Execute pulumi preview
python __main__.py preview

# Execute pulumi up
python __main__.py

# Execute pulumi destroy
python __main__.py destroy
```

For more information about the Pulumi Automation API, see [Pulumi Automation API](https://www.pulumi.com/docs/reference/pulumi-automation-api/).
