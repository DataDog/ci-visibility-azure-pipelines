
function Invoke-Parallel([scriptblock]$ScriptBlock, [array]$InputObject, [int]$ThrottleLimit = 5) {
    $jobs = New-Object System.Collections.Queue
    $result = New-Object System.Collections.Generic.List[object]

    $runScript = {
        param($item)
        & $ScriptBlock $item
    }

    foreach ($item in $InputObject) {
        if ($jobs.Count -ge $ThrottleLimit) {
            $job = $jobs.Dequeue()
            $result.Add($job.EndInvoke($job.AsyncWaitHandle))
        }
        $job = $runScript.BeginInvoke($item)
        $jobs.Enqueue($job)
    }

    while ($jobs.Count -gt 0) {
        $job = $jobs.Dequeue()
        $result.Add($job.EndInvoke($job.AsyncWaitHandle))
    }

    return $result
}

class AzureClient {
    [Microsoft.PowerShell.Commands.WebRequestSession]$Session
    [string]$Org
    [hashtable]$ConsumerInputs

    AzureClient([Microsoft.PowerShell.Commands.WebRequestSession]$session, [string]$org, [string]$ddSite, [string]$ddApiKey) {
        $this.Session = $session
        $this.Org = $org
        $this.ConsumerInputs = @{
            'datadog_site' = $ddSite
            'api_key' = $ddApiKey
        }
    }

    [array]ListProjects([string[]]$projectNames, [string]$continuationToken) {
        $params = @{}
        if ($continuationToken) {
            $params['continuationToken'] = $continuationToken
        }

        $response = $this.Session.Get("${azureApiRoot}/$($this.Org)/_apis/projects", $params)
        $data = $response.Content | ConvertFrom-Json

        if (!$projectNames) {
            $projects = $data.value
        } else {
            $projects = $data.value | Where-Object { $projectNames -contains $_.name }
        }

        $continuationToken = $data.continuation_token
        if ($continuationToken) {
            $projects += $this.ListProjects($projectNames, $continuationToken)
        }

        return $projects
    }

    [hashtable]ListSubscriptions([string]$eventType, [string[]]$projectIds) {
        $params = @{
            'consumerId' = $consumerId
            'eventType' = $eventType
        }

        $response = $this.Session.Get("${azureApiRoot}/$($this.Org)/_apis/hooks/subscriptions", $params)
        $subscriptions = $response.Content | ConvertFrom-Json | Select-Object -ExpandProperty value | Where-Object { $projectIds -contains $_.publisherInputs.projectId } | Group-Object -AsHashTable -Property { $_.publisherInputs.projectId }

        return $subscriptions
    }

    [hashtable]CreateSubscription([hashtable]$project, [string]$eventType) {
        $data = @{
            'publisherId' = 'pipelines'
            'eventType' = $eventType
            'consumerId' = $consumerId
            'consumerActionId' = 'performAction'
            'publisherInputs' = @{
                'projectId' = $project['id']
            }
            'consumerInputs' = $this.ConsumerInputs
        }

        $params = @{
            'api-version' = '7.0'
        }

        $response = $this.Session.Post("${azureApiRoot}/$($this.Org)/_apis/hooks/subscriptions", ($data | ConvertTo-Json), $params)
        $subscription = $response.Content | ConvertFrom-Json

        return $subscription
    }

    ReplaceSubscription([hashtable]$project, [string]$eventType, [string]$subscriptionId) {
        $params = @{
            'subscriptionId' = $subscriptionId
        }

        $data = @{
            'publisherId' = 'pipelines'
            'eventType' = $eventType
            'consumerId' = $consumerId
            'consumerActionId' = 'performAction'
            'publisherInputs' = @{
                'projectId' = $project['id']
            }
            'consumerInputs' = $this.ConsumerInputs
        }

        $response = $this.Session.Put("${azureApiRoot}/$($this.Org)/_apis/hooks/subscriptions", ($data | ConvertTo-Json), $params)
    }

    DeleteSubscription([string]$subscriptionId) {
        $params = @{
            'subscriptionId' = $subscriptionId
        }

        $response = $this.Session.Delete("${azureApiRoot}/$($this.Org)/_apis/hooks/subscriptions", $params)
    }

    [hashtable]GetExtension() {
        $params = @{
            'api-version' = '7.0-preview.1'
        }

        $response = $this.Session.Get("${azureExtensionApiRoot}/$($this.Org)/_apis/extensionmanagement/installedextensionsbyname/$($extensionId)", $params)
        if ($response.StatusCode -eq 404) {
            return $null
        }

        $extension = $response.Content | ConvertFrom-Json
        return $extension
    }

    [hashtable]InstallExtension() {
        $params = @{
            'api-version' = '7.0-preview.1'
        }

        $response = $this.Session.Post("${azureExtensionApiRoot}/$($this.Org)/_apis/extensionmanagement/installedextensionsbyname/$($extensionId)", $null, $params)
        $extension = $response.Content | ConvertFrom-Json

        return $extension
    }
}


param (
    [string]$ddApiKey,
    [string]$ddSite = "datadoghq.com",
    [string]$azUser,
    [string]$azToken,
    [string]$azOrg,
    [string[]]$projects,
    [switch]$uninstall,
    [int]$threads = 1,
    [string]$logLevel = "INFO"
)

function ValidateApiKey([string]$apiKey) {
    if ($apiKey.Length -lt 32) {
        throw "Datadog API Key must be at least 32 characters long"
    }
    return $apiKey
}

function CreateHttpSession([string]$auth) {
    $session = New-Object -TypeName Microsoft.PowerShell.Commands.WebRequestSession
    $session.Headers.Add("Accept", "application/json;api-version=7.0")
    $session.Authorization = "Basic " + [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($auth))
    return $session
}

$ddApiKey = ValidateApiKey($ddApiKey)
$auth = "${azUser}:${azToken}"
$session = CreateHttpSession $auth

. .\AzureClient.ps1
$client = New-AzureClient -Session $session -Org $azOrg -DdSite $ddSite -DdApiKey $ddApiKey

$extension = $client.GetExtension()
if (!$extension) {
    $doInstall = Read-Host "The extension ${EXTENSION_ID} is not installed. Install it now? (Y/N)"
    if ($doInstall.ToUpper() -eq "Y") {
        $client.InstallExtension()
        Write-Host "Extension installed"
    } else {
        exit
    }
}

$action = "Installing"
if ($uninstall) {
    $action = "Uninstalling"
}
if ($projects) {
    Write-Host "${action} hooks for projects ${projects}"
} else {
    Write-Host "${action} hooks for all projects in ${azOrg}"
}

$projectsList = $client.ListProjects($projects)
$projectIds = $projectsList.Id
$webhookEvents = @(
    'ms.vss-pipelines.run-state-changed-event',
    'ms.vss-pipelines.stage-state-changed-event',
    'ms.vss-pipelines.job-state-changed-event'
)
$subscriptions = @{ }
foreach ($event in $webhookEvents) {
    $subscriptions[$event] = $client.ListSubscriptions($event, $projectIds)
}

$JobScriptBlock = {
    param($project, $event, $client, $uninstall, $subscriptions)
    $currentSubscription = $subscriptions[$event][$project.Id]
    if ($uninstall -and $currentSubscription) {
        $client.DeleteSubscription($currentSubscription.Id)
        Write-Host "Hook ${event} for project ${project.Name} deleted"
    } else {
        if (!$currentSubscription) {
            $client.CreateSubscription($project, $event)
            Write-Host "Hook ${event} for project ${project.Name} created"
        } else {
            $client.ReplaceSubscription($project, $event, $currentSubscription.Id)
            Write-Host "Hook ${event} for project ${project.Name} updated"
        }
        Write-Host "${project.Name} hook: ${event} installed"
}
}

$jobs = @()
foreach ($project in $projectsList) {
foreach ($event in $webhookEvents) {
$job = @{
'ScriptBlock' = $JobScriptBlock
'ArgumentList' = $project, $event, $client, $uninstall, $subscriptions
}
$jobs += $job
}
}

$throttleLimit = [Math]::Max(1, $threads)
Invoke-Parallel -InputObject $jobs -ThrottleLimit $throttleLimit -ScriptBlock ([scriptblock]::Create('param($job) &$($job.ScriptBlock) @($job.ArgumentList)'))

Write-Host "Finished!"
