# Contributing

First of all, thanks for contributing!

This document provides some basic guidelines for contributing to this repository.
To propose improvements, feel free to submit a PR or open an Issue.

- [Documentation about the manifest in vss-extension.json](https://learn.microsoft.com/en-us/azure/devops/extend/develop/add-service-hook?view=azure-devops)
- [Documentation about the Azure DevOps REST APIs used in the service_hooks script](https://learn.microsoft.com/en-us/rest/api/azure/devops/hooks/subscriptions/create)
- [Documentation on how to package the extension for a new release](https://learn.microsoft.com/en-us/azure/devops/extend/publish/overview?toc=%2Fazure%2Fdevops%2Fmarketplace-extensibility%2Ftoc.json&view=azure-devops#package-your-extension) 


## Setup your Developer Environment

For the service_hooks.py script, only python3 and the requests package are needed.


## Releasing updates (Project maintainers)

For maintainers of the project, in order to release a new version of the extension the [tfx-cli](https://learn.microsoft.com/en-us/azure/devops/extend/publish/command-line?view=azure-devops#acquire-the-cross-platform-cli-for-azure-devops) is needed: 

```
npm install -g tfx-cli
```

We have 2 versions of the `vss-extension.json` file so that we can test changes in a private version of the extension before releasing them for everyone. Make the changes first in `vss-extension-dev.json`. Keep in mind every small change needs to increase the version number at the top. Package a new version with:

```
npx tfx-cli extension create --manifests ./vss-extension-dev.json
```

Then upload the generated file through the [Azure Marketplace](https://marketplace.visualstudio.com/manage/publishers/datadog). If you don't have permissions for this you need to reach out to a maintainer that has them.

After testing the changes in the private version of the extension just follow the same steps but this time in the file `vss-extension.json`:

```
npx tfx-cli extension create
```

And upload it again through the [Azure Marketplace](https://marketplace.visualstudio.com/manage/publishers/datadog) to the public version of the extension.


## Submit Issues

Many great ideas for new features come from the community, and we'd be happy to consider yours!

To share your request, you can open an issue
with the details about what you'd like to see. At a minimum, please provide:

- The goal of the new feature;
- A description of how it might be used or behave;
- Links to any important resources (e.g. Github repos, websites, screenshots,
  specifications, diagrams).


## Found a bug?

You can submit bug reports concerning the Datadog CI Visibility Azure DevOps Extension by
opening a Github issue. Please provide:

- A description of the problem;
- Expected behavior;
- Actual behavior;
- Errors (with stacktraces) or warnings received;
- Any details you can share about your Azure DevOps environment

If at all possible, also provide:

- An explanation of what causes the bug and/or how it can be fixed.


## Have a patch?

We welcome code contributions to the extension, which you can submit as a pull request.
Before you submit a PR, make sure another Issue or PR with the same goal doesn't
already exist.

To create a pull request:

1. **Fork the repository**
2. **Make any changes** for your patch;
4. **Update any relevant documentation**;
5. **Submit the pull request** from your fork back to this repository

A project member will review the changes with you. At a minimum, to be accepted and merged, pull
requests must:

- Have a stated goal and detailed description of the changes made;
- Include thorough test coverage and documentation, where applicable;
- Pass all tests on CI;
- Receive at least one approval from a project member of the Datadog CI Visibility team.

Make sure that your code is clean and readable, and that your commits are small and
atomic, with a proper commit message.
