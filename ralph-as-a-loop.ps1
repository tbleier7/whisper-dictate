#!/usr/bin/env pwsh
# ralph-as-a-loop.ps1 — runs Claude Code in a loop to work through a plan file

param(
    [Parameter(Mandatory)]
    [int]$Iterations,
    [Parameter(Mandatory)]
    [int]$Issue
)

$prompt = @"
GitHub issue #$Issue
@progress.txt
1. Read the GitHub issue and progress file.
2. Find the next incomplete acceptance criterion and implement it. This should be the one YOU decide has the highest priority - not necessarily the first one in the list.
4. Update progress.txt with what you did and tick off the acceptance criteria on the ticket so that a human can check the progress in the ticket
ONLY DO ONE ACCEPTANCE CRITERION AT A TIME.
5. Append the the token usage of your context window for the completed acceptance criterion in a textfile named after your issue (issue<IssueNumber>.txt). Use the template: <Acceptance Criteria>:<Usage in ContextWindow> Tokens
If, while implementing the feature, you notice that all work \
is complete, output <promise>COMPLETE</promise>. \
"@

for ($i = 1; $i -le $Iterations; $i++) {
    Write-Host "--- Iteration $i of $Iterations ---"

    $allLines = [System.Collections.Generic.List[string]]::new()
    claude --permission-mode acceptEdits -p $prompt --output-format stream-json | ForEach-Object {
        $allLines.Add($_)
        try {
            $ev = $_ | ConvertFrom-Json -ErrorAction Stop
            switch ($ev.type) {
                'assistant' {
                    foreach ($block in $ev.message.content) {
                        if ($block.type -eq 'text') { Write-Host $block.text }
                        elseif ($block.type -eq 'tool_use') { Write-Host "[tool: $($block.name)]" -ForegroundColor Cyan }
                    }
                }
                'result' { Write-Host "[result: $($ev.subtype)]" -ForegroundColor DarkGray }
            }
        } catch {}
    }
    $result = $allLines -join "`n"

    if ($result -like "*<promise>COMPLETE</promise>*") {
        Write-Host "PRD complete, exiting."
        exit 0
    }
}

# Example: .\ralph-as-a-loop.ps1 -Iterations 5 -Issue 42
