#!/usr/bin/env pwsh
# ralph-as-a-loop.ps1 — runs Claude Code in a loop to work through a plan file

param(
    [Parameter(Mandatory)]
    [int]$Iterations
)

$prompt = @"
@progress.txt
1. Read the PRD.md and progress file.
2. Find the next incomplete section in the PRD and and implement it. This should be the one YOU decide has the highest priority - not necessarily the first one in the list.
4. Update progress.txt with what you did and tick off the acceptance criteria on the ticket so that a human can check the progress in the ticket
ONLY DO ONE SECTION AT A TIME.
5. Append the the token usage of your context window for the completed SECTION in a textfile named after the section header (<sectionheader>.txt). Use the template: <sectionheader>:<Usage in ContextWindow> Tokens
If, while implementing the feature, you notice that all work \
is complete, output <promise>COMPLETE</promise>. \
"@

for ($i = 1; $i -le $Iterations; $i++) {
    Write-Host "--- Iteration $i of $Iterations ---"

    $result = claude --permission-mode acceptEdits -p $prompt

    Write-Host $result

    if ($result -like "*<promise>COMPLETE</promise>*") {
        Write-Host "PRD complete, exiting."
        exit 0
    }
}

# Example: .\ralph-as-a-loop.ps1 -Iterations 5 -Issue 42
