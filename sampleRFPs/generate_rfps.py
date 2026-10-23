"""
Generates synthetic (fictional) RFP documents for a medical-industry procurement:
  Enterprise EMR & Clinical Workflow Platform for Meridian Care Hospitals.

All organisations, people, certificates and figures are invented for classroom use.
Run:  python generate_rfps.py
"""
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (ListFlowable, ListItem, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)))
RFP_NO = "MCH-EMR-2026-01"
ss = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=ss["Normal"], fontSize=9.6, leading=13.2, spaceAfter=5)
H1 = ParagraphStyle("h1", parent=ss["Heading1"], fontSize=17, leading=21, spaceAfter=4,
                    textColor=colors.HexColor("#0B3C5D"))
H2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=12, leading=15, spaceBefore=9,
                    spaceAfter=4, textColor=colors.HexColor("#0B3C5D"))
SUB = ParagraphStyle("sub", parent=BODY, textColor=colors.HexColor("#555555"), fontSize=9)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=8.6, leading=11, spaceAfter=0)
CELLB = ParagraphStyle("cellb", parent=CELL, fontName="Helvetica-Bold")


def table(header, rows, widths, total_row=False):
    """Build a styled ReportLab table flowable for a PDF document.

    Args:
        header: Column heading values.
        rows: Table body rows, each containing one value per column.
        widths: Column widths measured in centimeters.
        total_row: Whether to shade the final row as a total.

    Returns:
        Configured ReportLab Table flowable.
    """
    data = [[Paragraph(str(h), CELLB) for h in header]]
    for r in rows:
        data.append([Paragraph(str(c), CELL) for c in r])
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCE9F2")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9AA5AE")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if total_row:
        style.append(("BACKGROUND", (0, len(data) - 1), (-1, len(data) - 1), colors.HexColor("#F1F5F8")))
    t.setStyle(TableStyle(style))
    return t


def bullets(items):
    """Build a bulleted list flowable from paragraph strings.

    Args:
        items: Text for each bullet item.

    Returns:
        ReportLab ListFlowable containing the requested bullets.
    """
    return ListFlowable([ListItem(Paragraph(i, BODY), leftIndent=12) for i in items],
                        bulletType="bullet", start="-", leftIndent=12)


def render(filename, title, subtitle, blocks, footer_label):
    """Render structured content blocks as a paginated synthetic PDF.

    Args:
        filename: Output PDF filename within the sampleRFPs directory.
        title: Main document title.
        subtitle: Subtitle shown below the title.
        blocks: Sequence of heading, paragraph, bullet, or table block tuples.
        footer_label: Organization label printed in each page footer and metadata.

    Returns:
        None. Writes the PDF to disk.
    """
    def on_page(canvas, doc):
        """Draw the fictional-use label and page number on a PDF page.

        Args:
            canvas: ReportLab canvas for the page being rendered.
            doc: Document template containing the current page number.

        Returns:
            None. Draws footer text directly on the canvas.
        """
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(2 * cm, 1.2 * cm, f"{footer_label}  |  Synthetic document for classroom use - fictional data")
        canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(os.path.join(OUT, filename), pagesize=A4, leftMargin=2 * cm,
                            rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=2 * cm,
                            title=title, author=footer_label)
    story = [Paragraph(title, H1), Paragraph(subtitle, SUB), Spacer(1, 6)]
    for kind, *args in blocks:
        if kind == "h":
            story.append(Paragraph(args[0], H2))
        elif kind == "p":
            story.append(Paragraph(args[0], BODY))
        elif kind == "b":
            story.append(bullets(args[0]))
            story.append(Spacer(1, 4))
        elif kind == "t":
            story.append(table(*args))
            story.append(Spacer(1, 6))
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)


def price_block(items, assumptions):
    """Build reusable commercial pricing content and calculate its total.

    Args:
        items: (label, INR-lakh amount, pricing basis) tuples.
        assumptions: List of pricing assumptions to render as bullets.

    Returns:
        Pair of (document block list, total price in INR lakh).
    """
    total = sum(a for _, a, _ in items)
    rows = [[l, f"{a:,}", n] for l, a, n in items]
    rows.append(["<b>Total 5-year cost</b>", f"<b>{total:,}</b>", f"<b>= INR {total / 100:.2f} crore</b>"])
    return [
        ("t", ["Cost component", "INR lakh", "Basis"], rows, [6.2, 2.4, 8.4], True),
        ("p", "<b>Pricing assumptions</b>"),
        ("b", assumptions),
    ], total


# ----------------------------------------------------------------------------------------
# 0. The procurement request (common to all suppliers)
# ----------------------------------------------------------------------------------------
def build_request():
    """Generate the synthetic buyer request PDF shared by all suppliers.

    Args:
        None.

    Returns:
        None. Writes the RFP request PDF to the sampleRFPs directory.
    """
    blocks = [
        ("h", "1. Background"),
        ("p", "Meridian Care Hospitals (MCH) is a fictional network of four multi-specialty hospitals with "
              "1,200 inpatient beds and about 3,500 clinical and administrative users. Patient records are "
              "currently split between a legacy hospital information system, departmental spreadsheets and "
              "paper charts. MCH intends to adopt a single Electronic Medical Record (EMR) and clinical "
              "workflow platform across all four sites."),
        ("h", "2. Scope of work"),
        ("b", [
            "Core EMR: patient registration, longitudinal record, clinical notes, problem list, allergies, orders and results.",
            "Computerised physician order entry (CPOE), e-prescribing and drug-interaction / allergy checking.",
            "Interfaces to the Laboratory Information System, Radiology/PACS and pharmacy using HL7 v2 and FHIR R4; DICOM for imaging.",
            "Integration with the national digital health ecosystem (ABHA / ABDM) for patient identity and record exchange.",
            "Patient portal and mobile app for appointments, reports and consent management.",
            "Migration of the last 5 years of patient demographics and clinical history from the legacy system.",
            "Training for about 3,500 users and post go-live hypercare.",
        ]),
        ("h", "3. Mandatory requirements"),
        ("b", [
            "Target go-live at all four hospitals within 9 months of contract signature (up to 12 months acceptable with justification).",
            "Platform availability of at least 99.9% with defined disaster-recovery objectives (RPO and RTO to be stated).",
            "Patient data hosted in India; encryption in transit and at rest; role-based access with a complete audit trail.",
            "Compliance with the Digital Personal Data Protection Act, 2023; information-security certification (e.g. ISO 27001) preferred.",
            "24x7 support for critical incidents with stated response and resolution times.",
            "A fixed-price commercial proposal covering a 5-year total cost of ownership with all assumptions listed.",
        ]),
        ("h", "4. Required structure of the response"),
        ("p", "Responses must be 2 to 4 pages and cover: executive summary; proposed solution and implementation "
              "approach; timeline, team and milestones; price table with assumptions; security, compliance and risk "
              "controls; support model, relevant experience and references. Statements that are not backed by "
              "evidence (numbers, certificates, named references) will be scored conservatively."),
        ("h", "5. Evaluation criteria"),
        ("t", ["Criterion", "Weight", "What will be assessed"], [
            ["Technical Capability", "30%", "Architecture, interoperability (HL7/FHIR/DICOM/ABDM), scalability, clinical fit"],
            ["Implementation Plan", "20%", "Timeline, milestones, staffing, training, data migration, risk plan"],
            ["Commercial Value", "20%", "Pricing clarity, 5-year total cost, assumptions and exclusions"],
            ["Security & Compliance", "20%", "Controls, certifications, privacy, auditability, data residency"],
            ["Support & Experience", "10%", "Support model and SLAs, similar projects, references"],
        ], [4.2, 1.6, 11.2]),
        ("h", "6. Key dates"),
        ("p", "RFP issued: 01 August 2026. Questions closed: 25 August 2026. Proposal submission deadline: 15 September 2026. "
              "Contact for clarifications: procurement@meridiancare.example (fictional)."),
    ]
    render("00_RFP_Request_MCH-EMR-2026-01.pdf",
           "Request for Proposal: Enterprise EMR and Clinical Workflow Platform",
           f"Meridian Care Hospitals  |  RFP No. {RFP_NO}  |  Issued 01 August 2026", blocks,
           f"MCH RFP {RFP_NO}")


# ----------------------------------------------------------------------------------------
# 1. Apex Health Systems - strong technical + security, higher price, moderate schedule
# ----------------------------------------------------------------------------------------
def build_apex():
    """Generate the fictional Apex Health Systems proposal PDF.

    Args:
        None.

    Returns:
        Total five-year price in INR lakh.
    """
    price, total = price_block([
        ("Platform subscription (5 years)", 620, "Per-bed tiered licence, 1,200 beds, includes patient portal"),
        ("Implementation and configuration", 310, "Fixed price, 11-month programme"),
        ("Data migration (5 years history)", 140, "Includes three full migration rehearsals"),
        ("Interfaces (LIS, PACS, pharmacy, ABDM)", 190, "Up to 15 interfaces; additional at INR 5 lakh each"),
        ("Training and change management", 60, "3,500 users, train-the-trainer model"),
        ("Support and maintenance (5 years)", 540, "24x7 L1-L3 support, includes minor upgrades"),
    ], [
        "Prices are in INR lakh, exclusive of GST at the prevailing rate.",
        "Hosting on a dual-availability-zone Indian cloud region is included in the subscription.",
        "Price is valid for 120 days from 12 September 2026; annual escalation capped at 4% after year 3.",
        "Excluded: client-side hardware, network upgrades at hospital sites, third-party licence fees for PACS.",
    ])
    blocks = [
        ("h", "1. Executive summary"),
        ("p", "Apex Health Systems Pvt. Ltd. (Pune) proposes the Apex CareCore platform, a cloud-native, FHIR-native EMR "
              "designed for multi-hospital groups. We understand that MCH needs one longitudinal patient record across four "
              "hospitals, dependable integration with laboratory, imaging and pharmacy systems, and a defensible security "
              "posture under the DPDP Act. Our proposal prioritises technical robustness and compliance over lowest price."),
        ("h", "2. Proposed solution and approach"),
        ("p", "CareCore stores clinical data natively as FHIR R4 resources in a clinical data repository, so that exchange with "
              "ABDM and other FHIR systems requires no translation layer. An event-driven integration layer (message broker "
              "with HL7 v2.5 adapters and DICOMweb gateway) connects the LIS, RIS/PACS and pharmacy systems. CareCore is "
              "ABDM-certified for the HIP and HIU roles."),
        ("b", [
            "Microservices architecture, horizontally scalable; a March 2026 load test sustained 9,200 concurrent sessions with p95 response under 1.4 seconds.",
            "Active-active deployment across two availability zones; RPO 5 minutes, RTO 30 minutes; 99.95% monthly availability commitment.",
            "Clinical decision support engine with drug-drug, drug-allergy and dose-range checking, configurable by the MCH pharmacy committee.",
            "Open APIs (FHIR REST, SMART on FHIR) so MCH can add third-party apps without vendor lock-in.",
        ]),
        ("h", "3. Timeline, team and milestones"),
        ("p", "We propose an 11-month programme with a pilot at one hospital before wave rollout. The programme team has 28 "
              "full-time equivalents at peak, led by a Programme Director and a Clinical Informatics Lead."),
        ("t", ["Phase", "Period", "Milestone / deliverable"], [
            ["Mobilise and design", "Month 1-2", "Signed-off functional design, interface catalogue, migration plan"],
            ["Build and integrate", "Month 2-6", "Configured platform, all interfaces tested in staging"],
            ["Pilot hospital go-live", "Month 7", "Hospital 1 live; pilot exit review"],
            ["Rollout waves", "Month 8-10", "Hospitals 2, 3 and 4 live in sequence"],
            ["Stabilise and handover", "Month 11", "Hypercare closure, handover to support"],
        ], [4.6, 2.6, 9.8]),
        ("p", "Top delivery risks are interface readiness at the legacy LIS, clinician availability for design workshops, and "
              "data quality in migrated records. Each is tracked in a risk log reviewed fortnightly with the MCH steering committee. "
              "Note that our 11-month schedule is longer than the 9-month target; the extra time buys a pilot-first rollout."),
        ("h", "4. Price"),
    ] + price + [
        ("h", "5. Security, compliance and risk controls"),
        ("b", [
            "Certifications: ISO/IEC 27001:2022, ISO/IEC 27701 and SOC 2 Type II (report dated January 2026); all held by Apex for the CareCore platform.",
            "Encryption: TLS 1.3 in transit, AES-256 at rest, field-level encryption for sensitive notes; keys managed in an HSM-backed key vault.",
            "Access: role- and attribute-based access control, mandatory multi-factor authentication, time-boxed break-glass access with automatic review.",
            "Auditability: immutable audit log of every read and write, retained for 8 years and exportable to MCH's SIEM.",
            "Privacy: data residency in India; consent management mapped to DPDP Act obligations; Data Protection Officer appointed; breach notification to the customer within 6 hours.",
            "Assurance: annual penetration test by a CERT-In empanelled auditor; the latest summary is available under NDA.",
        ]),
        ("h", "6. Support model, experience and references"),
        ("p", "Support is available 24x7 through three tiers. Priority 1 incidents receive a 15-minute response and a 4-hour "
              "resolution target; service credits apply if the 99.95% availability commitment is missed. After the 8-week "
              "hypercare period, support is remote; on-site engineers can be added as an option."),
        ("p", "Apex has completed 6 hospital EMR deployments in India over the last 5 years, the largest being a 900-bed teaching "
              "hospital. References: Lakeview Teaching Hospital (900 beds, live 2024), Sahyadri Heart Institute (350 beds, live 2023), "
              "Coastal Medicare Group (3 hospitals, 620 beds, live 2025). Reference contacts will be provided on shortlisting."),
    ]
    render("01_Apex_Health_Systems_RFP_Response.pdf", "Apex Health Systems - Proposal",
           f"Response to RFP {RFP_NO}  |  Submitted 12 September 2026  |  Contact: bids@apexhealth.example", blocks,
           "Apex Health Systems proposal")
    return total


# ----------------------------------------------------------------------------------------
# 2. BrightPath HealthTech - lowest price, fast timeline, weak compliance, limited experience
# ----------------------------------------------------------------------------------------
def build_brightpath():
    """Generate the fictional BrightPath HealthTech proposal PDF.

    Args:
        None.

    Returns:
        Total five-year price in INR lakh.
    """
    price, total = price_block([
        ("Platform subscription (5 years)", 400, "Flat SaaS fee, includes patient portal"),
        ("Implementation and configuration", 190, "Fixed price, 6-month programme"),
        ("Data migration", 80, "Last 2 years of records only"),
        ("Interfaces", 110, "Includes 3 interfaces (LIS, PACS, pharmacy)"),
        ("Training", 30, "Online sessions and recorded videos"),
        ("Support (5 years)", 310, "Business-hours support, 24x7 for P1 by phone"),
    ], [
        "Prices are in INR lakh, exclusive of GST.",
        "Each interface beyond the first three is charged at INR 6 lakh.",
        "ABDM integration is offered as an optional add-on and is not included in the total above.",
        "Travel, on-site training and migration of records older than 2 years are excluded and charged at actuals.",
    ])
    blocks = [
        ("h", "1. Executive summary"),
        ("p", "BrightPath HealthTech offers the fastest and most cost-effective route to a modern EMR for Meridian Care "
              "Hospitals. Our SaaS platform, BrightChart, is simple to configure and can be live in all four hospitals in "
              "6 months. We believe MCH should not pay for features it will not use in the first years."),
        ("h", "2. Proposed solution and approach"),
        ("p", "BrightChart is a modular SaaS EMR with registration, clinical notes, orders, e-prescribing and a patient portal. "
              "The platform supports HL7 and FHIR and can connect to laboratory and imaging systems. It is hosted on a public "
              "cloud region in India and scales to meet demand. Standard templates will be used for most clinical workflows to "
              "keep configuration effort low."),
        ("h", "3. Timeline, team and milestones"),
        ("p", "We recommend a single go-live at all four hospitals at the end of month 6, supported by a team of 12 people."),
        ("t", ["Phase", "Period", "Milestone / deliverable"], [
            ["Kick-off and configuration", "Month 1-3", "Configured platform"],
            ["Testing and training", "Month 4-5", "User acceptance testing, online training"],
            ["Go-live", "Month 6", "All hospitals live together"],
        ], [4.6, 2.6, 9.8]),
        ("p", "Risks will be managed through weekly project meetings."),
        ("h", "4. Price"),
    ] + price + [
        ("h", "5. Security and compliance"),
        ("p", "We follow industry best practices for security and encrypt patient data. ISO 27001 certification is in progress "
              "and expected in Q1 2027. Data is hosted in India. A detailed compliance mapping and details of access controls "
              "and audit logging can be provided on request."),
        ("h", "6. Support and experience"),
        ("p", "Support is available from 9 am to 6 pm, Monday to Saturday, with a phone line for critical issues outside these "
              "hours. BrightPath has deployed BrightChart at 2 sites: a 60-bed clinic and an 85-bed nursing home, both in 2025. "
              "Reference: Greenfield Nursing Home (85 beds)."),
    ]
    render("02_BrightPath_HealthTech_RFP_Response.pdf", "BrightPath HealthTech - Proposal",
           f"Response to RFP {RFP_NO}  |  Submitted 14 September 2026  |  Contact: sales@brightpath.example", blocks,
           "BrightPath HealthTech proposal")
    return total


# ----------------------------------------------------------------------------------------
# 3. NexaWorks Medical - balanced, strongest implementation plan and support model
# ----------------------------------------------------------------------------------------
def build_nexa():
    """Generate the fictional NexaWorks Medical proposal PDF.

    Args:
        None.

    Returns:
        Total five-year price in INR lakh.
    """
    price, total = price_block([
        ("Platform subscription (5 years)", 510, "Per-bed licence, 1,200 beds, includes patient portal"),
        ("Implementation and configuration", 270, "Fixed price, 9-month programme"),
        ("Data migration (5 years history)", 120, "Includes two full rehearsals and clinical validation"),
        ("Interfaces (LIS, PACS, pharmacy, ABDM)", 150, "Up to 12 interfaces; additional at INR 4 lakh each"),
        ("Training and super-user programme", 70, "3,500 users, simulation lab, floor-walkers"),
        ("Support and resident engineers (5 years)", 370, "24x7 support; resident engineers in year 1"),
    ], [
        "Prices are in INR lakh, exclusive of GST; valid for 90 days from submission.",
        "Hosting in two Indian data centres (primary and disaster recovery) is included.",
        "Annual support escalation capped at 3% from year 2; price protection for additional beds at the same per-bed rate.",
        "Excluded: client-side hardware and hospital network upgrades; PACS third-party licences.",
    ])
    blocks = [
        ("h", "1. Executive summary"),
        ("p", "NexaWorks Medical proposes NexaCare, a configurable EMR platform used by multi-hospital groups, delivered through a "
              "phased and clinician-led programme. We understand that for MCH the greatest risks are not software features but "
              "clinical adoption, interface readiness and stability during go-live. Our proposal is built around controlling those risks."),
        ("h", "2. Proposed solution and approach"),
        ("p", "NexaCare combines a configurable clinical core with a commercial integration engine supporting HL7 v2, FHIR R4 "
              "and DICOM through a PACS gateway. ABDM milestones M1 to M3 are already certified. The platform has been "
              "tested with 5,000 concurrent users and is deployed in a primary data centre with a disaster-recovery site "
              "(RPO 15 minutes, RTO 2 hours, 99.9% availability). Order sets and clinical pathways are configured with MCH "
              "clinicians rather than imposed as templates."),
        ("h", "3. Implementation plan, timeline and team"),
        ("p", "The 9-month plan uses a pilot ward, a pilot hospital and two further waves, each gated by acceptance criteria "
              "agreed in advance with MCH. The 24-person core team includes named leads: Programme Director (Rohan Mehta), "
              "Clinical Informatics Lead (Dr. Kavita Rao, a practising physician), Integration Lead, Data Migration Lead and "
              "Training Lead. MCH nominates a clinical champion per department."),
        ("t", ["Phase", "Period", "Milestone / acceptance gate"], [
            ["Mobilise", "Week 1-4", "Governance in place, workshops scheduled, interface catalogue draft"],
            ["Design", "Week 5-10", "Signed-off clinical workflows per department (14 departments)"],
            ["Build and integrate", "Week 8-20", "All 12 interfaces passing end-to-end tests with sample data"],
            ["Migration rehearsals", "Week 14-26", "Two rehearsals with 99.5% reconciliation of patient records"],
            ["Pilot ward and Hospital 1", "Week 22-26", "Go/no-go review; safety sign-off by CMIO"],
            ["Hospitals 2, 3, 4", "Week 28-36", "One go-live every 3 weeks; each gated on previous hypercare exit"],
            ["Hypercare", "8 weeks per site", "Daily huddles, floor-walkers, defect SLA tracking"],
        ], [4.6, 2.6, 9.8]),
        ("t", ["Key risk", "Likelihood / impact", "Mitigation and owner"], [
            ["Legacy LIS interface delay", "Medium / High", "Early interface sandbox in week 3; fallback file-based exchange (Integration Lead)"],
            ["Low clinician availability", "High / Medium", "Protected design-workshop slots in contract; backfill for super-users (Clinical Lead)"],
            ["Migration data-quality issues", "Medium / High", "Two rehearsals, clinical validation of samples (Data Migration Lead)"],
            ["Adoption resistance", "Medium / High", "1 super-user per 25 users; simulation lab; floor-walkers (Training Lead)"],
        ], [4.6, 3.2, 9.2]),
        ("h", "4. Price"),
    ] + price + [
        ("h", "5. Security, compliance and risk controls"),
        ("b", [
            "Certification: ISO/IEC 27001:2022 certified; SOC 2 audit planned for 2027.",
            "Encryption in transit (TLS 1.2+) and at rest (AES-256); role-based access with multi-factor authentication.",
            "Audit trail of all record access, retained for 7 years; data hosted in India.",
            "Mapping of platform controls to DPDP Act, 2023 provided in Annex A of the contract; annual penetration test by an external auditor.",
        ]),
        ("h", "6. Support model, experience and references"),
        ("t", ["Priority", "Response", "Resolution target", "Coverage"], [
            ["P1 - system down / patient safety", "15 minutes", "2 hours", "24x7, on-site within 4 hours"],
            ["P2 - major function degraded", "30 minutes", "8 hours", "24x7"],
            ["P3 - minor issue", "4 hours", "3 working days", "Business hours"],
        ], [5.2, 2.8, 3.6, 5.4]),
        ("p", "Support is tiered (L1 service desk, L2 application, L3 engineering). A named Customer Success Manager runs "
              "monthly service reviews, and resident engineers are placed at each hospital for 12 months after go-live. "
              "Service credits of up to 15% of the quarterly support fee apply if SLAs are missed. A knowledge base and "
              "in-app guided help reduce ticket volume."),
        ("p", "NexaWorks has completed 8 hospital deployments over 6 years. References: Riverside Medical Centre (480 beds, "
              "live 2024), Unity Hospitals Group (3 hospitals, 750 beds, live 2025), Sunrise Women's Hospital (200 beds, live 2023)."),
    ]
    render("03_NexaWorks_Medical_RFP_Response.pdf", "NexaWorks Medical - Proposal",
           f"Response to RFP {RFP_NO}  |  Submitted 12 September 2026  |  Contact: tenders@nexaworks.example", blocks,
           "NexaWorks Medical proposal")
    return total


# ----------------------------------------------------------------------------------------
# 4. Orbit Digital Health - strong experience, vague integration plan, medium price
# ----------------------------------------------------------------------------------------
def build_orbit():
    """Generate the fictional Orbit Digital Health proposal PDF.

    Args:
        None.

    Returns:
        Total five-year price in INR lakh.
    """
    price, total = price_block([
        ("Platform subscription (5 years)", 540, "Per-bed licence, 1,200 beds"),
        ("Implementation and configuration", 280, "Fixed price, 10-month programme"),
        ("Data migration", 130, "5 years of history"),
        ("Integration", 160, "Fixed price; all required interfaces included"),
        ("Training", 55, "Classroom and on-the-job training"),
        ("Support (5 years)", 355, "24x7 helpdesk, regional support centre"),
    ], [
        "Prices are in INR lakh, exclusive of GST; valid for 90 days.",
        "Integration effort is included for the interfaces required by MCH, as finalised during design.",
        "Annual support escalation of 5% from year 2.",
        "Excluded: hardware and network upgrades at MCH sites.",
    ])
    blocks = [
        ("h", "1. Executive summary"),
        ("p", "Orbit Digital Health has implemented hospital information systems for 11 years and has completed 22 hospital "
              "deployments, more than any other bidder, and we are proud of the satisfaction of our customers. OrbitOne is a proven, "
              "mature EMR platform. Our proposal focuses on the confidence that comes from delivering many similar projects."),
        ("h", "2. Proposed solution and approach"),
        ("p", "OrbitOne covers registration, clinical documentation, orders, e-prescribing and a patient portal. The solution "
              "will integrate with the Hospital's existing systems using standard interfaces. The detailed interface list and "
              "specifications will be finalised during the design phase, and integration effort is included in the price. The "
              "platform scales as needed by adding servers and is deployed on Orbit-managed infrastructure in India."),
        ("h", "3. Timeline, team and milestones"),
        ("p", "The implementation will take 10 months following a standard Orbit methodology and will be led by an "
              "experienced project manager supported by functional consultants."),
        ("t", ["Phase", "Period", "Milestone / deliverable"], [
            ["Planning and design", "Month 1-3", "Design documents"],
            ["Configuration and integration", "Month 3-7", "System ready for testing"],
            ["Testing and training", "Month 7-9", "UAT complete, users trained"],
            ["Go-live and support", "Month 10", "All hospitals live"],
        ], [4.6, 2.6, 9.8]),
        ("h", "4. Price"),
    ] + price + [
        ("h", "5. Security and compliance"),
        ("p", "Orbit is ISO/IEC 27001 certified. The platform uses encryption for data at rest and in transit, role-based "
              "access, and maintains audit logs. Orbit is compliant with applicable Indian data-protection regulations. "
              "Patient data is stored in India."),
        ("h", "6. Support model, experience and references"),
        ("p", "Orbit's helpdesk operates 24x7 with a regional support centre in Hyderabad and Delhi. Critical issues are "
              "responded to within 30 minutes. A customer satisfaction score of 4.6 out of 5 was recorded in Orbit's 2025 "
              "customer survey."),
        ("t", ["Reference hospital", "Beds", "Go-live", "Scope"], [
            ["Deccan General Hospital", "850", "2023", "EMR, CPOE, portal"],
            ["Harmony Hospitals (3 sites)", "1,100", "2024", "EMR, LIS and pharmacy interfaces"],
            ["Eastern Cardiac Centre", "300", "2022", "EMR, cardiology modules"],
            ["Valley Children's Hospital", "250", "2025", "EMR, paediatric workflows"],
            ["Metro Multispecialty Hospital", "600", "2021", "EMR, billing"],
            ["Orchid Women's Hospital", "180", "2024", "EMR, maternity workflows"],
            ["Northern District Hospital", "420", "2023", "EMR, PACS integration"],
            ["Sapphire Health City", "700", "2022", "EMR, CPOE"],
            ["Tri-City Medical Institute", "520", "2025", "EMR, patient portal"],
        ], [6.0, 2.0, 2.4, 6.6]),
    ]
    render("04_Orbit_Digital_Health_RFP_Response.pdf", "Orbit Digital Health - Proposal",
           f"Response to RFP {RFP_NO}  |  Submitted 10 September 2026  |  Contact: rfp@orbitdigital.example", blocks,
           "Orbit Digital Health proposal")
    return total


# ----------------------------------------------------------------------------------------
# 5. Zenith MedSoft - deliberately incomplete (edge-case test: missing sections and evidence)
# ----------------------------------------------------------------------------------------
def build_zenith():
    """Generate the deliberately incomplete fictional Zenith proposal PDF.

    Args:
        None.

    Returns:
        None. Writes the incomplete proposal PDF to the sampleRFPs directory.
    """
    blocks = [
        ("h", "1. Executive summary"),
        ("p", "Zenith MedSoft is a growing healthcare software company. We are pleased to respond to the MCH RFP and believe our "
              "ZenithEMR product is a good fit for a modern hospital group."),
        ("h", "2. Proposed solution"),
        ("p", "ZenithEMR provides patient registration, clinical notes, orders and reports. Interfaces to other systems are "
              "possible. Our product roadmap includes FHIR support and a patient app."),
        ("h", "3. Timeline"),
        ("p", "The project would take approximately 8 to 12 months depending on the final scope. A detailed project plan "
              "will be shared after contract award."),
        ("h", "4. Commercial proposal"),
        ("p", "Pricing will be discussed after a requirement workshop. We are confident that our price will be competitive."),
        ("h", "6. Support and experience"),
        ("p", "Zenith has a dedicated support team and has worked with several clients in the healthcare sector. Customer "
              "references can be provided later."),
    ]
    render("05_Zenith_MedSoft_RFP_Response_INCOMPLETE.pdf", "Zenith MedSoft - Proposal",
           f"Response to RFP {RFP_NO}  |  Submitted 15 September 2026  |  Contact: info@zenithmedsoft.example", blocks,
           "Zenith MedSoft proposal")


if __name__ == "__main__":
    build_request()
    totals = {"Apex": build_apex(), "BrightPath": build_brightpath(), "NexaWorks": build_nexa(), "Orbit": build_orbit()}
    build_zenith()
    print("Totals (INR lakh):", totals)
