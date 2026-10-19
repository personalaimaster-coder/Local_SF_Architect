"""Synthetic Salesforce-CLI-output generators for hermetic tests.

Phase 0's golden tests originally ran against a real corpus captured from a
private Salesforce project. That client-derived data was removed from the repo
(see MEMORY.md sec.5/sec.10); these generators reproduce the *shape* of each
command family's output so the filters can be validated on the same ratios and
signal-preservation guarantees without shipping any proprietary data.

All content here is fabricated (generic "SampleClass"/"CompNNN" names).
"""

import json


def table_output(n_rows=2000, kind="ApexClass"):
    """Box-drawing table like `sf project retrieve preview` / `sf org list metadata`.

    Header row carries a hint token so the table filter keeps it; every data row
    starts with the box pipe and collapses to a single count line.
    """
    head = [
        "Retrieved / Listed Source",
        "=========================",
        "\u250c" + "\u2500" * 16 + "\u252c" + "\u2500" * 14 + "\u252c" + "\u2500" * 8 + "\u2510",
        "\u2502 Full Name       \u2502 Type         \u2502 State  \u2502",
        "\u251c" + "\u2500" * 16 + "\u253c" + "\u2500" * 14 + "\u253c" + "\u2500" * 8 + "\u2524",
    ]
    rows = [
        "\u2502 Comp{:06d}     \u2502 {:<12} \u2502 Add    \u2502".format(i, kind)
        for i in range(n_rows)
    ]
    foot = ["\u2514" + "\u2500" * 16 + "\u2534" + "\u2500" * 14 + "\u2534" + "\u2500" * 8 + "\u2518"]
    return "\n".join(head + rows + foot)


def debug_log(noise=5000, n_debug=5):
    """Apex debug log: mostly HEAP_ALLOCATE / METHOD_ENTRY noise + a few signals.

    Returns (raw_text, [signal_lines_that_must_survive]).
    """
    lines = []
    for i in range(noise):
        lines.append("12:00:00.{} ({})|HEAP_ALLOCATE|[{}]|Bytes:8".format(i % 9, i, i % 50))
        lines.append("12:00:00.{} ({})|SYSTEM_METHOD_ENTRY|[{}]|Foo.bar()".format(i % 9, i, i))
    signals = []
    for j in range(n_debug):
        d = "12:00:0{}.0 (900{})|USER_DEBUG|[{}]|DEBUG|checkpoint {}".format(j % 9, j, j, j)
        signals.append(d)
        lines.append(d)
    fatal = "12:00:09.9 (99999)|FATAL_ERROR|System.NullPointerException: boom"
    limit = "12:00:09.9 (99998)|LIMIT_USAGE_FOR_NS|(default)|SOQL|5|100"
    signals.extend([fatal, limit])
    lines.extend([fatal, limit])
    return "\n".join(lines), signals


def query_json(n=500):
    """`sf data query --json` payload with a records[] list (CSV-reprojectable)."""
    records = []
    for i in range(n):
        records.append({
            "attributes": {
                "type": "ApexClass",
                "url": "/services/data/v60.0/sobjects/ApexClass/00X{:015d}".format(i),
            },
            "Id": "00X{:015d}".format(i),
            "Name": "SampleClass{}".format(i),
            "NamespacePrefix": None,
            "Status": "Active",
            "ApiVersion": 60.0,
        })
    obj = {"status": 0, "result": {"totalSize": n, "done": True, "records": records}}
    return json.dumps(obj, indent=2)


def describe_json(n_fields=300):
    """`sf sobject describe --json` payload (no records[] -> minify path)."""
    fields = []
    for i in range(n_fields):
        fields.append({
            "name": "Field{}__c".format(i),
            "label": "Sample Field {}".format(i),
            "type": "string",
            "length": 255,
            "nillable": True,
            "custom": True,
            "updateable": True,
            "createable": True,
        })
    obj = {"status": 0, "result": {"name": "SampleObject", "fields": fields,
                                   "childRelationships": []}}
    return json.dumps(obj, indent=2)


def deploy_report(n_components=300):
    """`sf project deploy validate` report: status/summary + many Succeeded rows."""
    lines = [
        "=== Deploy Validate",
        "Status: Failed",
        "Deploy ID: 0Af000000000001AAA",
        "Elapsed Time: 12.34s",
        "Components: {}".format(n_components),
    ]
    lines += ["Component MyComp{}  ApexClass  Succeeded".format(i) for i in range(n_components)]
    lines.append("Error  classes/Broken.cls  Missing ';' (line 3)")
    return "\n".join(lines)


def apex_test(n_pass=200):
    """`sf apex run test` human output: summary block + passing rows + coverage."""
    lines = [
        "=== Test Summary",
        "Outcome              Passed",
        "Tests Ran            {}".format(n_pass + 1),
        "Pass Rate            98%",
        "Fail Rate            2%",
        "Test Run Id          707000000000001",
        "Org Wide Coverage    82%",
        "Time Elapsed         45.6s",
    ]
    lines += ["MyTest.method{}  Pass  {}ms".format(i, 30 + i) for i in range(n_pass)]
    lines.append("BrokenTest.checkThing  Fail  System.AssertException: expected 1, got 2")
    lines.append("=== Apex Code Coverage by Class")
    lines.append("RiskyClass    40%   12,14,18")
    lines.append("HealthyClass  95%")
    return "\n".join(lines)
