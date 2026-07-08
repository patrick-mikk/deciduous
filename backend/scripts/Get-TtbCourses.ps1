<#
.SYNOPSIS
    Query the UofT Timetable Builder (TTB) API for every course in a term and
    export the results to JSON and CSV.

.DESCRIPTION
    Pages through POST https://api.easi.utoronto.ca/ttb/getPageableCourses for the
    given session(s) and division(s), collects all courses, and writes:
      - <OutDir>\TTB_<label>_courses.json   full course objects (catalog + sections)
      - <OutDir>\TTB_<label>_courses.csv    one row per course (key fields)
      - <OutDir>\TTB_<label>_sections.csv   one row per section/meeting time

    A no-match search returns HTTP 404 from TTB; that is treated as "0 results".

.PARAMETER Session
    TTB session code. Default 20269 = Fall 2026.
    (20265 = Summer 2026, 20271 = Winter 2027, 20269-20271 = Fall-Winter full year.)

.PARAMETER Divisions
    Division codes to include. Default ARTSC (Faculty of Arts & Science).

.PARAMETER AllDivisions
    Ignore -Divisions and pull the full division list from /reference-data
    (ARTSC, APSC, ERIN, SCAR, MUSIC, ARCLA, FIS, FPEH) — i.e. truly all courses.

.PARAMETER PageSize
    Results per request (default 100).

.PARAMETER OutDir
    Output directory (default: current directory).

.EXAMPLE
    .\Get-TtbCourses.ps1
    # All Arts & Science courses in Fall 2026.

.EXAMPLE
    .\Get-TtbCourses.ps1 -AllDivisions
    # Every course in Fall 2026 across all faculties.

.EXAMPLE
    .\Get-TtbCourses.ps1 -Session 20265 -OutDir .\data
    # All Arts & Science courses in Summer 2026, written to .\data.

.NOTES
    Compatible with Windows PowerShell 5.1 and PowerShell 7+.
    The TTB API is undocumented and public/read-only. Be polite: this script
    throttles between requests. See backend/docs/TTB_API_REFERENCE.md.
#>

[CmdletBinding()]
param(
    [string]   $Session      = "20269",        # Fall 2026
    [string[]] $Divisions    = @("ARTSC"),
    [switch]   $AllDivisions,
    [int]      $PageSize      = 100,
    [string]   $OutDir        = ".",
    [int]      $ThrottleMs    = 150
)

$ErrorActionPreference = "Stop"
$Base    = "https://api.easi.utoronto.ca/ttb"
$Headers = @{ "Accept" = "application/json"; "Origin" = "https://ttb.utoronto.ca" }

function Invoke-Ttb {
    param([string]$Path, [string]$Method = "Get", $Body = $null)
    try {
        if ($Method -eq "Post") {
            return Invoke-RestMethod -Uri ($Base + $Path) -Method Post -Headers $Headers `
                -ContentType "application/json; charset=utf-8" -Body $Body
        }
        return Invoke-RestMethod -Uri ($Base + $Path) -Method Get -Headers $Headers
    }
    catch {
        $code = $null
        if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
        if ($code -eq 404) { return $null }   # TTB: 404 == no results
        throw
    }
}

function New-SearchBody {
    param([string]$Division, [int]$Page)
    $payload = @{
        courseCodeAndTitleProps = @{
            courseCode             = ""
            courseTitle            = ""
            courseSectionCode      = ""
            searchCourseDescription = $false
        }
        departmentProps = @(); campuses = @(); requirementProps = @()
        instructorProps = @(); courseLevels = @(); deliveryModes = @()
        dayPreferences  = @(); timePreferences = @(); creditWeights = @()
        sessions        = @($Session)
        divisions       = @($Division)
        availableSpace  = $false
        waitListable    = $false
        page            = $Page
        pageSize        = $PageSize
        direction       = "asc"
    }
    return ($payload | ConvertTo-Json -Depth 8 -Compress)
}

function Get-HtmlText {
    param([string]$Html)
    if ([string]::IsNullOrWhiteSpace($Html)) { return "" }
    $t = $Html -replace "<[^>]+>", ""            # strip tags
    $t = $t -replace "&amp;", "&" -replace "&lt;", "<" -replace "&gt;", ">" -replace "&nbsp;", " "
    $t = $t -replace ([char]0x00A0), " "         # real non-breaking space
    $t = $t -replace ([char]0x2019), "'" -replace ([char]0x2013), "-" -replace ([char]0x2014), "-"
    return ($t -replace "\s+", " ").Trim()
}

function Format-Time {
    param([int]$MillisOfDay)
    $m = [math]::Floor($MillisOfDay / 60000)
    return ("{0:00}:{1:00}" -f [math]::Floor($m / 60), ($m % 60))
}
$DayName = @{ 1 = "Mon"; 2 = "Tue"; 3 = "Wed"; 4 = "Thu"; 5 = "Fri"; 6 = "Sat"; 7 = "Sun" }

# --- resolve divisions --------------------------------------------------------
if ($AllDivisions) {
    Write-Host "Fetching division list from /reference-data ..." -ForegroundColor Cyan
    $ref = Invoke-Ttb -Path "/reference-data"
    $Divisions = @($ref.payload.divisions | ForEach-Object { $_.value })
}
Write-Host ("Session {0} | divisions: {1}" -f $Session, ($Divisions -join ", ")) -ForegroundColor Cyan

# --- collect courses ----------------------------------------------------------
$allCourses = New-Object System.Collections.ArrayList
foreach ($div in $Divisions) {
    $page = 1
    $total = $null
    $collected = 0          # actual courses collected for this division
    do {
        $resp = Invoke-Ttb -Path "/getPageableCourses" -Method Post -Body (New-SearchBody -Division $div -Page $page)
        if ($null -eq $resp -or $null -eq $resp.payload) {
            if ($page -eq 1) { Write-Host ("  {0}: 0 courses" -f $div) -ForegroundColor DarkYellow }
            break
        }
        $pc = $resp.payload.pageableCourse
        if ($null -eq $total) { $total = [int]$pc.total }
        # TTB enforces its own page size (~20) and ignores large pageSize values,
        # so track the real count returned rather than assuming full pages.
        $n = ($pc.courses | Measure-Object).Count
        foreach ($c in $pc.courses) { [void]$allCourses.Add($c) }
        $collected += $n
        Write-Host ("  {0}: page {1} -> {2}/{3}" -f $div, $page, $collected, $total)
        $page++
        Start-Sleep -Milliseconds $ThrottleMs
    } while ($collected -lt $total -and $n -gt 0)
}

Write-Host ("Collected {0} course offerings." -f $allCourses.Count) -ForegroundColor Green
if ($allCourses.Count -eq 0) {
    Write-Warning "No courses returned. The session may not be published in TTB yet (Fall-Winter is typically loaded mid-summer). Try -Session 20265 (Summer 2026) to verify connectivity."
    return
}

# --- write outputs ------------------------------------------------------------
if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }
$label = "Fall2026"
switch ($Session) {
    "20265" { $label = "Summer2026" }
    "20269" { $label = "Fall2026" }
    "20271" { $label = "Winter2027" }
    "20269-20271" { $label = "FallWinter2026-27" }
    default { $label = "Session$Session" }
}
$stamp   = Get-Date -Format "yyyyMMdd"
$jsonOut = Join-Path $OutDir ("TTB_{0}_courses_{1}.json"  -f $label, $stamp)
$csvOut  = Join-Path $OutDir ("TTB_{0}_courses_{1}.csv"   -f $label, $stamp)
$secOut  = Join-Path $OutDir ("TTB_{0}_sections_{1}.csv"  -f $label, $stamp)

$allCourses | ConvertTo-Json -Depth 12 | Out-File -FilePath $jsonOut -Encoding utf8

$courseRows = foreach ($c in $allCourses) {
    $cm = $c.cmCourseInfo
    [pscustomobject]@{
        Code         = $c.code
        Title        = $c.name
        SectionCode  = $c.sectionCode
        Credit       = $c.maxCredit
        Campus       = $c.campus
        Breadth      = ($cm.breadthRequirements -join "; ")
        Distribution = ($cm.distributionRequirements -join "; ")
        Prerequisite = (Get-HtmlText $cm.prerequisitesText)
        Corequisite  = (Get-HtmlText $cm.corequisitesText)
        Exclusion    = (Get-HtmlText $cm.exclusionsText)
        Sections     = ($c.sections | Measure-Object).Count
        Description  = (Get-HtmlText $cm.description)
    }
}
$courseRows | Sort-Object Code | Export-Csv -Path $csvOut -NoTypeInformation -Encoding UTF8

$sectionRows = foreach ($c in $allCourses) {
    foreach ($s in $c.sections) {
        $mt = foreach ($m in $s.meetingTimes) {
            if ($null -ne $m.start) {
                ("{0} {1}-{2}" -f $DayName[[int]$m.start.day], (Format-Time $m.start.millisofday), (Format-Time $m.end.millisofday))
            }
        }
        $instr = ($s.instructors | ForEach-Object { ("{0} {1}" -f $_.firstName, $_.lastName).Trim() }) -join "; "
        [pscustomobject]@{
            Code           = $c.code
            Title          = $c.name
            Section        = $s.name
            TeachMethod    = $s.teachMethod
            Meetings       = ($mt -join " | ")
            CurrentEnrol   = $s.currentEnrolment
            MaxEnrol       = $s.maxEnrolment
            Waitlist       = $s.currentWaitlist
            Instructors    = $instr
        }
    }
}
$sectionRows | Sort-Object Code, Section | Export-Csv -Path $secOut -NoTypeInformation -Encoding UTF8

Write-Host ""
Write-Host ("Wrote:")            -ForegroundColor Green
Write-Host ("  {0}  ({1} courses)"  -f $jsonOut, $allCourses.Count)
Write-Host ("  {0}  ({1} courses)"  -f $csvOut,  $courseRows.Count)
Write-Host ("  {0}  ({1} sections)" -f $secOut,  ($sectionRows | Measure-Object).Count)
