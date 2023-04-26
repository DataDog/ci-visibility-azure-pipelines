# Datadog CI Visibility Azure Pipelines Extension

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## Overview

With this extension for [Datadog CI Visibility](https://www.datadoghq.com/product/ci-cd-monitoring/#pipeline-visibility), you can more quickly connect your Azure Pipelines to Datadog to gain comprehensive visibility into the performance of your pipelines, stages, and jobs.
​
​
## How it works
​
**What you'll need from Datadog**

- API Key: Your Datadog API key. This key is created by your [Datadog organization](https://docs.datadoghq.com/account_management/api-app-keys/).
- Datadog site: Which [Datadog site](https://docs.datadoghq.com/getting_started/site/) to connect and send data to.

**Setting up the integration**

Install this Datadog CI Visibility for Azure Pipelines extension in your Azure organization. This will install a [webhook consumer](https://learn.microsoft.com/en-us/azure/devops/extend/develop/add-service-hook?view=azure-devops).

After the extension is installed, you can use it from the [Service hooks](https://learn.microsoft.com/en-us/azure/devops/service-hooks/overview?view=azure-devops) section within your Project Settings in Azure Pipelines.

**All 3 supported types of events are required** and must be enabled individually. If one or more events are not enabled, the installation will be incomplete and lead to unexpected behavior in Datadog. The events are:

- run state changed
- run stage state changed
- run job state changed

## Enabling multiple projects in bulk

If you want to enable the hooks for many or all your Azure projects we provide a [script](https://raw.githubusercontent.com/DataDog/ci-visibility-azure-pipelines/main/service_hooks.py) to help you do it through the Azure API. For this you'll need:

- Azure DevOps username
- Azure DevOps [API Token](https://learn.microsoft.com/en-us/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate?view=azure-devops&tabs=Windows#create-a-pat)
- Azure DevOps organization name

For more info:
```
service_hooks.py --help
```

​
## Other resources
- [Datadog documentation](https://docs.datadoghq.com/continuous_integration/pipelines/azure/)
- [What is Datadog CI Visibility?](https://www.datadoghq.com/blog/datadog-ci-visibility/)
- [Extension in the Azure Marketplace](https://marketplace.visualstudio.com/items?itemName=Datadog.ci-visibility)
